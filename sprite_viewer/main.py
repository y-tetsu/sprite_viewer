import pygame
import json
import sys
import os
import argparse

INFO_MARGIN_LEFT = 180
MIN_SCREEN_WIDTH = 300
MIN_SCREEN_HEIGHT = 300
SCALE_MIN = 1
SCALE_MAX = 12

def load_data(base_name):
    json_path = base_name + ".json"
    image_path = base_name + ".png"

    if not os.path.exists(json_path) or not os.path.exists(image_path):
        print(f"Error: '{json_path}' または '{image_path}' が見つかりません。")
        raise FileNotFoundError(f"'{json_path}' or '{image_path}' not found.")

    with open(json_path) as f:
        data = json.load(f)
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
    raise ValueError(f"Invalid size format: {s} (例: 800x600)")

def main(spritesheet="spritesheet", scale=6, bg_color=(50, 50, 50), screen_size=None, border=1):
    pygame.init()
    pygame.display.set_mode((1, 1))

    data, sheet = load_data(spritesheet)
    frame_width = data["frame_width"]
    frame_height = data["frame_height"]
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
            "[View  ] H / V / L / SPACE"
        ]

        for i, line in enumerate(info_lines):
            text = font.render(line, True, (255, 255, 255))
            screen.blit(text, (10, 10 + i * 20))

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="スプライトアニメーションビューワ")
    parser.add_argument("spritesheet", nargs="?", default="spritesheet", help="スプライトシートのベース名（拡張子なし）")
    parser.add_argument("--scale", type=int, default=6, help="表示倍率（例: 4）")
    parser.add_argument("--bg", type=str, default="#323232", help="背景色（例: #000000）")
    parser.add_argument("--size", type=str, help="画面サイズ（例: 800x600）")
    parser.add_argument("--border", type=int, default=1, help="各フレーム間の枠線幅（ピクセル、デフォルト: 1）")

    args = parser.parse_args()

    try:
        bg_color = parse_color(args.bg)
        screen_size = parse_size(args.size) if args.size else None
    except ValueError as e:
        print("引数エラー:", e)
        sys.exit(1)

    main(
        spritesheet=args.spritesheet,
        scale=args.scale,
        bg_color=bg_color,
        screen_size=screen_size,
        border=args.border
    )

