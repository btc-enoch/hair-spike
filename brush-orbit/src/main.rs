//! Headless orbit renderer: load a Gaussian-splat .ply, render a turntable of
//! cameras around the subject using Brush's Metal rasterizer, write PNG frames.
//! Stitch to mp4 with ffmpeg afterwards.
//!
//! usage: brush-orbit <ply> <outdir> [frames] [dist_mult] [elev] [fov] [size]
use anyhow::{Context, Result, anyhow};
use brush_process::burn_init_setup;
use brush_render::camera::Camera;
use brush_render::gaussian_splats::SplatRenderMode;
use brush_render::kernels::camera_model::CameraModel;
use brush_render::{Splats, TextureMode, render_splats};
use brush_serde::load_splat_from_ply;
use glam::{Mat3, Quat, Vec2, Vec3, uvec2};
use std::io::Cursor;

fn median(mut v: Vec<f32>) -> f32 {
    v.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    v[v.len() / 2]
}
fn pctl(mut v: Vec<f32>, p: f32) -> f32 {
    v.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    v[(((v.len() - 1) as f32) * p) as usize]
}

#[tokio::main(flavor = "multi_thread")]
async fn main() -> Result<()> {
    let a: Vec<String> = std::env::args().collect();
    let ply = a.get(1).context("usage: brush-orbit <ply> <outdir> [frames] [dist_mult] [elev] [fov] [size]")?;
    let outdir = a.get(2).context("need outdir")?;
    let frames: usize = a.get(3).and_then(|s| s.parse().ok()).unwrap_or(120);
    let dist_mult: f32 = a.get(4).and_then(|s| s.parse().ok()).unwrap_or(2.5);
    let elev: f32 = a.get(5).and_then(|s| s.parse().ok()).unwrap_or(0.2);
    let fov: f32 = a.get(6).and_then(|s| s.parse().ok()).unwrap_or(0.7);
    let size: u32 = a.get(7).and_then(|s| s.parse().ok()).unwrap_or(720);
    // Constrain the orbit to the captured front arc (full 360 visits angles that
    // were never filmed -> floater mush). Face was ~180deg in the test render.
    let az_center: f32 = a.get(8).and_then(|s| s.parse().ok()).unwrap_or(180.0);
    let az_sweep: f32 = a.get(9).and_then(|s| s.parse().ok()).unwrap_or(140.0);

    std::fs::create_dir_all(outdir)?;
    // burn_init_setup returns a raw WgpuDevice; into_splats wants a burn
    // tensor Device — convert via .into() (per brush-render's render test).
    let device: burn::tensor::Device = burn_init_setup().await.into();

    let bytes = tokio::fs::read(ply).await?;
    let msg = load_splat_from_ply(Cursor::new(bytes), None)
        .await
        .map_err(|e| anyhow!("ply load: {e:?}"))?;
    let splats = msg.data.into_splats(&device, SplatRenderMode::Default);
    eprintln!("loaded {} splats", splats.num_splats());

    // Robust subject center/extent from the means (median + IQR ignores stray
    // far-away background gaussians).
    let md = splats.means().to_data_async().await.map_err(|e| anyhow!("readback: {e:?}"))?;
    let m = md.as_slice::<f32>().map_err(|e| anyhow!("{e:?}"))?;
    let n = m.len() / 3;
    let (mut xs, mut ys, mut zs) = (Vec::with_capacity(n), Vec::with_capacity(n), Vec::with_capacity(n));
    for i in 0..n {
        let (x, y, z) = (m[i * 3], m[i * 3 + 1], m[i * 3 + 2]);
        if x.is_finite() && y.is_finite() && z.is_finite() {
            xs.push(x);
            ys.push(y);
            zs.push(z);
        }
    }
    let center = Vec3::new(median(xs.clone()), median(ys.clone()), median(zs.clone()));
    // IQR (75-25) instead of 90-10 -> tighter, ignores spread-out background.
    let spread = Vec3::new(
        pctl(xs.clone(), 0.75) - pctl(xs, 0.25),
        pctl(ys.clone(), 0.75) - pctl(ys, 0.25),
        pctl(zs.clone(), 0.75) - pctl(zs, 0.25),
    );
    let radius = spread.length().max(0.1);
    let dist = radius * dist_mult;
    eprintln!("center={center:?} radius={radius:.3} dist={dist:.3}");

    // ---- floater cull: drop transparent / oversized / far-flung gaussians ----
    let opac_thr: f32 = a.get(10).and_then(|s| s.parse().ok()).unwrap_or(0.06);
    let scale_thr = radius * a.get(11).and_then(|s| s.parse().ok()).unwrap_or(0.35_f32);
    let keep_r = radius * a.get(12).and_then(|s| s.parse().ok()).unwrap_or(2.5_f32);
    let splats = if opac_thr > 0.0 {
        let rd = splats.rotations().to_data_async().await.map_err(|e| anyhow!("{e:?}"))?;
        let rot = rd.as_slice::<f32>().map_err(|e| anyhow!("{e:?}"))?;
        let ld = splats.log_scales().to_data_async().await.map_err(|e| anyhow!("{e:?}"))?;
        let lsc = ld.as_slice::<f32>().map_err(|e| anyhow!("{e:?}"))?;
        let sd = splats.sh_coeffs.val().to_data_async().await.map_err(|e| anyhow!("{e:?}"))?;
        let shd = sd.as_slice::<f32>().map_err(|e| anyhow!("{e:?}"))?;
        let rod_ = splats.raw_opacities.val().to_data_async().await.map_err(|e| anyhow!("{e:?}"))?;
        let rod = rod_.as_slice::<f32>().map_err(|e| anyhow!("{e:?}"))?;
        let opd_ = splats.opacities().to_data_async().await.map_err(|e| anyhow!("{e:?}"))?;
        let opd = opd_.as_slice::<f32>().map_err(|e| anyhow!("{e:?}"))?;
        let scd_ = splats.scales().to_data_async().await.map_err(|e| anyhow!("{e:?}"))?;
        let scd = scd_.as_slice::<f32>().map_err(|e| anyhow!("{e:?}"))?;
        let k = shd.len() / n; // SH coeffs (flattened) per gaussian
        let (mut pf, mut rf, mut sf, mut cf, mut of) =
            (Vec::new(), Vec::new(), Vec::new(), Vec::new(), Vec::new());
        let mut kept = 0usize;
        for i in 0..n {
            let (mx, my, mz) = (m[i * 3], m[i * 3 + 1], m[i * 3 + 2]);
            if !(mx.is_finite() && my.is_finite() && mz.is_finite()) {
                continue;
            }
            let maxs = scd[i * 3].max(scd[i * 3 + 1]).max(scd[i * 3 + 2]);
            let d = ((mx - center.x).powi(2) + (my - center.y).powi(2) + (mz - center.z).powi(2)).sqrt();
            if opd[i] >= opac_thr && maxs <= scale_thr && d <= keep_r {
                pf.extend_from_slice(&m[i * 3..i * 3 + 3]);
                rf.extend_from_slice(&rot[i * 4..i * 4 + 4]);
                sf.extend_from_slice(&lsc[i * 3..i * 3 + 3]);
                cf.extend_from_slice(&shd[i * k..i * k + k]);
                of.push(rod[i]);
                kept += 1;
            }
        }
        eprintln!("cull: kept {kept}/{n} (opac>={opac_thr}, maxscale<={scale_thr:.3}, dist<={keep_r:.3})");
        Splats::from_raw(pf, rf, sf, cf, of, SplatRenderMode::Default, &device)
    } else {
        splats
    };

    for i in 0..frames {
        let frac = if frames > 1 { i as f32 / (frames as f32 - 1.0) } else { 0.5 };
        let ang = (az_center + (frac - 0.5) * az_sweep).to_radians();
        let pos = center + Vec3::new(dist * ang.cos(), -elev * radius, dist * ang.sin());

        // Look-at rotation, COLMAP-style camera basis (x right, y down, z fwd).
        let fwd = (center - pos).normalize();
        let right = Vec3::Y.cross(fwd).normalize();
        let down = fwd.cross(right).normalize();
        let rot = Quat::from_mat3(&Mat3::from_cols(right, down, fwd));

        let cam = Camera::new(pos, rot, fov as f64, fov as f64, Vec2::splat(0.5), CameraModel::Pinhole);
        let (img, _) = render_splats(
            splats.clone(),
            &cam,
            uvec2(size, size),
            Vec3::ZERO,
            None,
            TextureMode::Float,
        )
        .await;
        let dat = img.to_data_async().await.map_err(|e| anyhow!("img readback: {e:?}"))?;
        let px = dat.as_slice::<f32>().map_err(|e| anyhow!("{e:?}"))?;
        let mut out = image::RgbImage::new(size, size);
        for y in 0..size {
            for x in 0..size {
                let idx = (((y * size + x) * 4) as usize).min(px.len() - 4);
                let to8 = |f: f32| (f.clamp(0.0, 1.0) * 255.0) as u8;
                out.put_pixel(x, y, image::Rgb([to8(px[idx]), to8(px[idx + 1]), to8(px[idx + 2])]));
            }
        }
        out.save(format!("{outdir}/frame_{i:04}.png"))?;
        if i % 20 == 0 {
            eprintln!("frame {i}/{frames}");
        }
    }
    eprintln!("done -> {outdir}");
    Ok(())
}
