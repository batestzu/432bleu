<script lang="ts">
    import { onMount } from "svelte";
    import { fade } from "svelte/transition";
    import { loaderProgressStore } from "../../Stores/LoaderStore";

    const W = 1412, H = 194;
    const LOOP_MS = 4200;

    let canvas: HTMLCanvasElement;

    function spacedText(ctx: CanvasRenderingContext2D, str: string, x: number, y: number, spacing: number) {
        let total = 0;
        for (const ch of str) total += ctx.measureText(ch).width + spacing;
        total -= spacing;
        let cx = x - total / 2;
        for (const ch of str) {
            const w = ctx.measureText(ch).width;
            ctx.fillText(ch, cx + w / 2, y);
            cx += w + spacing;
        }
    }

    function drawWordmark(ctx: CanvasRenderingContext2D, s: number, glowK: number) {
        const cx = W * s / 2, cy = H * s / 2 - 6 * s;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.font = `800 ${68 * s}px "Unbounded", sans-serif`;
        const part1 = "INTO THE ", part2 = "BLEU";
        const w1 = ctx.measureText(part1).width;
        const w2 = ctx.measureText(part2).width;
        const startX = cx - (w1 + w2) / 2;

        if (glowK > 0) {
            ctx.save();
            ctx.shadowBlur = 26 * s * glowK;
            ctx.shadowColor = "#00f0ff";
            ctx.fillStyle = "#eafcff";
            ctx.textAlign = "left";
            ctx.fillText(part1, startX, cy);
            ctx.shadowColor = "#ff2bd6";
            ctx.fillStyle = "#ff2bd6";
            ctx.fillText(part2, startX + w1, cy);
            ctx.restore();
        }

        ctx.textAlign = "left";
        ctx.fillStyle = "#eafcff";
        ctx.fillText(part1, startX, cy);
        ctx.fillStyle = "#ff2bd6";
        ctx.fillText(part2, startX + w1, cy);

        ctx.font = `500 ${12.5 * s}px "JetBrains Mono", monospace`;
        ctx.fillStyle = "rgba(95,230,221,0.72)";
        spacedText(ctx, "FREQUENCY · 432.000 Hz · MEMBERS ONLY", cx, cy + 50 * s, 2.4 * s);
    }

    function drawScene(ctx: CanvasRenderingContext2D, t: number, s: number) {
        const cx = W * s / 2, cy = H * s / 2;

        const bg = ctx.createRadialGradient(cx, H * s * 0.34, 0, cx, H * s * 0.34, W * s * 0.62);
        bg.addColorStop(0, "#08283a");
        bg.addColorStop(0.5, "#04121d");
        bg.addColorStop(1, "#02060a");
        ctx.fillStyle = bg;
        ctx.fillRect(0, 0, W * s, H * s);

        const N = 7, maxR = W * s * 0.62;
        ctx.lineWidth = 1.4 * s;
        for (let i = 0; i < N; i++) {
            const phase = (t + i / N) % 1;
            const r = 24 * s + phase * maxR;
            const a = Math.sin(phase * Math.PI) * 0.22;
            if (a <= 0) continue;
            ctx.beginPath();
            ctx.strokeStyle = `rgba(0,240,255,${a})`;
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.stroke();
        }
        for (let i = 0; i < 2; i++) {
            const phase = (t + i / 2 + 0.25) % 1;
            const r = 30 * s + phase * maxR * 0.8;
            const a = Math.sin(phase * Math.PI) * 0.10;
            if (a <= 0) continue;
            ctx.beginPath();
            ctx.strokeStyle = `rgba(255,43,214,${a})`;
            ctx.arc(W * s * 0.78, cy, r, 0, Math.PI * 2);
            ctx.stroke();
        }

        const sweepX = (-0.35 + t * 1.7) * W * s;
        const bandW = W * s * 0.5;
        const sweep = ctx.createLinearGradient(sweepX - bandW / 2, 0, sweepX + bandW / 2, 0);
        sweep.addColorStop(0, "rgba(0,240,255,0)");
        sweep.addColorStop(0.5, "rgba(120,245,255,0.07)");
        sweep.addColorStop(1, "rgba(0,240,255,0)");
        ctx.save();
        ctx.globalCompositeOperation = "lighter";
        ctx.fillStyle = sweep;
        ctx.fillRect(sweepX - bandW / 2, 0, bandW, H * s);
        ctx.restore();

        ctx.save();
        ctx.globalCompositeOperation = "overlay";
        ctx.fillStyle = "rgba(255,255,255,0.025)";
        for (let y = 0; y < H * s; y += 3 * s) ctx.fillRect(0, y, W * s, 1 * s);
        ctx.restore();

        const glowK = 0.7 + 0.35 * Math.sin(t * Math.PI * 2);
        drawWordmark(ctx, s, glowK);

        const vg = ctx.createLinearGradient(0, 0, W * s, 0);
        vg.addColorStop(0, "rgba(2,6,10,0.55)");
        vg.addColorStop(0.12, "rgba(2,6,10,0)");
        vg.addColorStop(0.88, "rgba(2,6,10,0)");
        vg.addColorStop(1, "rgba(2,6,10,0.55)");
        ctx.fillStyle = vg;
        ctx.fillRect(0, 0, W * s, H * s);
    }

    onMount(() => {
        const DPR = Math.min(window.devicePixelRatio || 1, 2);
        canvas.width = W * DPR;
        canvas.height = H * DPR;
        const ctx = canvas.getContext("2d")!;

        let animId: number;
        let started = false;

        function frame(now: number) {
            const t = (now % LOOP_MS) / LOOP_MS;
            drawScene(ctx, t, DPR);
            animId = requestAnimationFrame(frame);
        }

        function start() {
            if (!started) {
                started = true;
                animId = requestAnimationFrame(frame);
            }
        }

        Promise.all([
            document.fonts.load(`800 68px "Unbounded"`),
            document.fonts.load(`500 13px "JetBrains Mono"`),
        ])
            .then(() => document.fonts.ready)
            .then(start);

        setTimeout(start, 800);

        return () => cancelAnimationFrame(animId);
    });
</script>

<div
    class="absolute top-0 left-0 z-50 h-dvh w-dvw flex items-center justify-center"
    style="background:#02060a;"
    in:fade={{ duration: 100 }}
    out:fade={{ delay: 500, duration: 300 }}
>
    <div style="width:1412px;max-width:100vw;">
        <canvas bind:this={canvas} style="display:block;width:100%;height:auto;" />
        <div style="height:3px;background:#011a22;margin-top:8px;">
            <div
                style="height:100%;background:#00f0ff;transition:width 200ms;width:{$loaderProgressStore * 100}%;"
            />
        </div>
    </div>
</div>
