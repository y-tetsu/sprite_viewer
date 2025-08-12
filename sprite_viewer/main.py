import pygame
import json
import sys
import os
import argparse
from PIL import Image

INFO_MARGIN_LEFT = 180
MIN_SCREEN_WIDTH = 320
MIN_SCREEN_HEIGHT = 320
SCALE_MIN = 1
SCALE_MAX = 20

def load_data(json_path):
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    with open(json_path, "r") as f:
        data = json.load(f)

    image_path = data.get("image_path")
    if not image_path or not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found or not specified in JSON: {image_path}")

    image = pygame.image.load(image_path).convert_alpha()
    return data, image

def get_frame(sheet, index, fw, fh, columns, scale, border):
    x = (index % columns) * fw
    y = (index // columns) * fh
    frame = sheet.subsurface(pygame.Rect(x, y, fw + border, fh + border))
    if scale != 1:
        frame = pygame.transform.scale(frame, ((fw + border) * scale, (fh + border) * scale))
    return frame

def parse_color(s):
    s = s.lstrip('#')
    if len(s) == 6:
        return tuple(int(s[i:i+2], 16) for i in (0, 2, 4))
    raise ValueError(f"Invalid color code: {s}")

def parse_size(s):
    if 'x' in s:
        w, h = s.lower().split('x')
        return int(w), int(h)
    raise ValueError(f"Invalid size format: {s} (e.g., 800x600)")

def export_gif(anim_name, anim_info, sheet, fw, fh, columns, scale, border, flip_x, flip_y, fps):
    frames = []
    for idx in anim_info["frames"]:
        x = (idx % columns) * fw
        y = (idx // columns) * fh
        frame = sheet.subsurface(pygame.Rect(x + border, y + border, fw - border, fh - border))
        if scale != 1:
            frame = pygame.transform.scale(frame, ((fw - border) * scale, (fh - border) * scale))
        if flip_x or flip_y:
            frame = pygame.transform.flip(frame, flip_x, flip_y)
        pil_image = Image.frombytes("RGBA", frame.get_size(), pygame.image.tostring(frame, "RGBA"))
        frames.append(pil_image)

    if frames:
        duration = int(1000 / fps)
        frames[0].save(
            f"{anim_name}.gif",
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=0,
            transparency=0,
            disposal=2
        )
        print(f"[OK] Exported: {anim_name}.gif")
    else:
        print("[ERROR] No frames to export.")

def run_viewer(json_path, scale=18, bg_color=(50, 50, 50), screen_size=None):
    import os
    os.environ["SDL_VIDEO_CENTERED"] = "1"

    pygame.init()
    pygame.display.set_mode((1, 1))

    data, sheet = load_data(json_path)
    frame_width = data["frame_width"]
    frame_height = data["frame_height"]
    border = data["border"]
    fw, fh = frame_width + border, frame_height + border
    columns = sheet.get_width() // fw

    def compute_screen_size(scale):
        frame_px_w = fw * scale
        frame_px_h = fh * scale
        width = max(frame_px_w + INFO_MARGIN_LEFT + 10 * scale, MIN_SCREEN_WIDTH)
        height = max(frame_px_h + 20 * scale, MIN_SCREEN_HEIGHT)
        return (width, height)

    if screen_size is None:
        screen_size = compute_screen_size(scale)

    screen = pygame.display.set_mode(screen_size)
    pygame.display.set_caption("Sprite Viewer")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)

    animations = data["animations"]
    current_animation = 0

    flip_x = False
    flip_y = False
    force_loop = None
    paused = False

    def prepare_animation(index):
        info = animations[index % len(animations)]
        frames = [get_frame(sheet, idx, fw, fh, columns, scale, border) for idx in info["frames"]]
        return {
            "name": info["name"],
            "frames": frames,
            "fps": info.get("fps", 10),
            "loop": info.get("loop", True) if force_loop is None else force_loop,
            "index": 0,
            "time_acc": 0.0
        }

    anim = prepare_animation(current_animation)

    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if pygame.K_0 <= event.key <= pygame.K_9:
                    current_animation = (event.key - pygame.K_0) % len(animations)
                    anim = prepare_animation(current_animation)
                elif event.key == pygame.K_RIGHT:
                    if paused:
                        anim["index"] = (anim["index"] + 1) % len(anim["frames"])
                    else:
                        current_animation = (current_animation + 1) % len(animations)
                        anim = prepare_animation(current_animation)
                elif event.key == pygame.K_LEFT:
                    if paused:
                        anim["index"] = (anim["index"] - 1) % len(anim["frames"])
                    else:
                        current_animation = (current_animation - 1) % len(animations)
                        anim = prepare_animation(current_animation)
                elif event.key == pygame.K_h:
                    flip_x = not flip_x
                elif event.key == pygame.K_v:
                    flip_y = not flip_y
                elif event.key == pygame.K_l:
                    force_loop = not anim["loop"] if force_loop is None else not force_loop
                    anim = prepare_animation(current_animation)
                elif event.key == pygame.K_UP:
                    anim["fps"] = min(anim["fps"] + 1, 60)
                elif event.key == pygame.K_DOWN:
                    anim["fps"] = max(anim["fps"] - 1, 1)
                elif event.key in (pygame.K_EQUALS, pygame.K_KP_PLUS):
                    scale = min(scale + 1, SCALE_MAX)
                    screen_size = compute_screen_size(scale)
                    screen = pygame.display.set_mode(screen_size)
                    anim = prepare_animation(current_animation)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    scale = max(scale - 1, SCALE_MIN)
                    screen_size = compute_screen_size(scale)
                    screen = pygame.display.set_mode(screen_size)
                    anim = prepare_animation(current_animation)
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_g:
                    export_gif(anim['name'], animations[current_animation], sheet, fw, fh, columns, scale, border, flip_x, flip_y, anim["fps"])

        if not paused:
            anim["time_acc"] += dt
            frame_duration = 1.0 / anim["fps"]

            if anim["time_acc"] >= frame_duration:
                anim["time_acc"] -= frame_duration
                if anim["index"] + 1 < len(anim["frames"]):
                    anim["index"] += 1
                elif anim["loop"]:
                    anim["index"] = 0
                else:
                    anim["index"] = len(anim["frames"]) - 1

        screen.fill(bg_color)
        frame = anim["frames"][anim["index"]]
        if flip_x or flip_y:
            frame = pygame.transform.flip(frame, flip_x, flip_y)
        screen.blit(frame, (
            screen_size[0] // 2 - frame.get_width() // 2 + INFO_MARGIN_LEFT // 2,
            screen_size[1] // 2 - frame.get_height() // 2
        ))

        # 情報表示
        flip_text = ""
        if flip_x: flip_text += "H"
        if flip_y: flip_text += "V"
        if not flip_text: flip_text = "-"

        info_lines = [
            f"Anim: {anim['name']}",
            f"FPS : {anim['fps']}",
            f"Loop: {'ON' if anim['loop'] else 'OFF'}",
            f"Frame: {anim['index'] + 1} / {len(anim['frames'])}",
            f"Flip: {flip_text}",
            f"Scale: {scale}",
            f"Pause: {'ON' if paused else 'OFF'}",
            "",
            "[Select] 0–9",
            "[Anim  ] Left / Right",
            "[Frame ] Left / Right",
            "[Speed ] Up / Down",
            "[Zoom  ] + / -",
            "[View  ] H / V / L / SPACE",
            "[Export] G"
        ]

        for i, line in enumerate(info_lines):
            text = font.render(line, True, (255, 255, 255))
            screen.blit(text, (10, 10 + i * 20))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Sprite Animation Viewer")
    parser.add_argument("json_file", help="Path to animation definition JSON file (e.g., anim.json)")
    parser.add_argument("--scale", type=int, default=15, help="Display scale (e.g., 4)")
    parser.add_argument("--bg", type=str, default="#323232", help="Background color (hex format, e.g., #000000)")
    parser.add_argument("--size", type=str, help="Screen size (e.g., 800x600)")

    args = parser.parse_args()

    try:
        bg_color = parse_color(args.bg)
        screen_size = parse_size(args.size) if args.size else None
    except ValueError as e:
        print("Argument error:", e)
        sys.exit(1)

    run_viewer(
        json_path=args.json_file,
        scale=args.scale,
        bg_color=bg_color,
        screen_size=screen_size,
    )


if __name__ == "__main__":
    main()
