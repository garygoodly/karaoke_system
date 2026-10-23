"""Local-only WebSocket F0 service. Start separately in the uv environment.

Install: uv pip install --python .venv-uv/Scripts/python.exe torchcrepe websockets
"""
import argparse
import asyncio
import json
import struct
from collections import deque

import numpy as np


def estimate(samples, model, device, min_periodicity):
    import torch
    import torchcrepe
    audio = torch.tensor(samples, dtype=torch.float32, device=device).unsqueeze(0)
    with torch.inference_mode():
        hz, periodicity = torchcrepe.predict(
            audio, 16000, 160, 75, 900, model=model,
            batch_size=64, device=device, return_periodicity=True,
        )
    f = hz[0].detach().cpu().numpy()
    p = periodicity[0].detach().cpu().numpy()
    good = (p >= min_periodicity) & np.isfinite(f) & (f > 0)
    if not np.any(good):
        return {"hz": None, "periodicity": float(np.max(p)) if p.size else 0.0}
    # Last valid frames only, to avoid returning a stale pitch from an older vowel.
    tail = min(5, len(f))
    recent = good[-tail:]
    return {"hz": float(np.median(f[-tail:][recent])) if np.any(recent) else None,
            "periodicity": float(np.median(p[-tail:]))}


async def main(args):
    import torch
    import websockets
    model = args.model
    device = args.device
    if device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; use --device cpu')
    print('Loading torchcrepe; first inference may take time...', flush=True)
    # Browser snapshots are overlapping; process each snapshot independently.
    async def handle(ws):
        async for packet in ws:
            if not isinstance(packet, bytes) or len(packet) < 4100 or len(packet) > 100000:
                await ws.send(json.dumps({'error': 'Invalid audio packet'}));continue
            rate = struct.unpack_from('<I', packet, 0)[0]
            if rate < 8000 or rate > 192000 or (len(packet)-4) % 4:
                await ws.send(json.dumps({'error': 'Invalid sample rate'}));continue
            samples = np.frombuffer(packet, dtype='<f4', offset=4)
            if not np.isfinite(samples).all():
                await ws.send(json.dumps({'error': 'Invalid samples'}));continue
            # Resample one browser frame to 16 kHz, with interpolation.
            n = max(1024, int(round(len(samples)*16000/rate)))
            mono = np.interp(np.linspace(0, len(samples)-1, n),
                             np.arange(len(samples)), samples).astype(np.float32)
            if np.sqrt(np.mean(mono*mono)) < args.min_rms:
                result = {'hz': None, 'periodicity': 0.0}
            else:
                result = await asyncio.to_thread(estimate, mono, model, device, args.min_periodicity)
            await ws.send(json.dumps(result))
    async with websockets.serve(handle, '127.0.0.1', args.port, max_size=100000):
        print(f'Local torchcrepe ready at ws://127.0.0.1:{args.port}', flush=True)
        await asyncio.Future()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--device', choices=['cpu','cuda'], default='cpu')
    parser.add_argument('--model', choices=['tiny','full'], default='tiny')
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--min-rms', type=float, default=0.002)
    parser.add_argument('--min-periodicity', type=float, default=0.25)
    asyncio.run(main(parser.parse_args()))
