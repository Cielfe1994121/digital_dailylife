import pygame
import random
import math

# --- 設定パラメータ ---
WIDTH, HEIGHT = 800, 600
BG_COLOR = (20, 25, 35)  # 背景（夜の街）

# --- 水滴の設定（外側） ---
STATIC_DROP_COUNT = 2000  # びっしり張り付く数
STATIC_DROP_COLOR = (180, 200, 220)
FALLING_DROP_COLOR = (220, 230, 255)
SPAWN_SPEED = 30  # 雨がガラスに付着する速度

# --- 結露の設定（内側） ---
FOG_COLOR = (255, 255, 255)  # 白
FOG_MAX_ALPHA = 50  # ★初期状態のうっすら加減（最大値）
FOG_REGEN_SPEED = 0.05  # 戻る速度 (0.05 = 20フレームに1回)
WIPE_RADIUS = 15  # 指の太さ


class FallingDrop:
    """上から流れてきて、外側の水滴だけを巻き込む雨粒"""

    def __init__(self, x, vy):
        self.x = x
        self.y = -20
        self.r = random.randint(6, 10)
        self.vy = vy
        self.to_remove = False

    def update(self):
        self.y += self.vy
        if self.y > HEIGHT + 50:
            self.to_remove = True

    def draw(self, screen):
        # 本体
        pygame.draw.circle(
            screen, FALLING_DROP_COLOR, (int(self.x), int(self.y)), int(self.r)
        )
        # ハイライト
        off = int(self.r * 0.3)
        pygame.draw.circle(
            screen,
            (255, 255, 255),
            (int(self.x - off), int(self.y - off)),
            int(self.r * 0.3),
        )


def create_background():
    """ボケた夜景"""
    bg = pygame.Surface((WIDTH, HEIGHT))
    bg.fill(BG_COLOR)
    for _ in range(60):
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT)
        radius = random.randint(20, 80)
        color = random.choice([(30, 50, 70), (70, 40, 30), (40, 40, 50)])
        for r in range(radius, 0, -5):
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*color, 3), (r, r), r)
            bg.blit(s, (x - r, y - r))
    return bg


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Rainy Window: White Fog Regeneration")
    clock = pygame.time.Clock()

    background = create_background()

    # --- 外側の世界：静止水滴 ---
    static_drops = []
    for _ in range(STATIC_DROP_COUNT):
        static_drops.append(
            [random.randint(0, WIDTH), random.randint(0, HEIGHT), random.randint(1, 3)]
        )

    # 外側の世界：落ちてくる雨粒
    falling_drops = []

    # --- 内側の世界：結露レイヤーシステム ---

    # 1. 現在の霧レイヤー
    # 初期状態： (255, 255, 255, 50) = うっすら白い
    fog_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    fog_surface.fill((*FOG_COLOR, FOG_MAX_ALPHA))

    # 2. ★修正ポイント：回復用レイヤー
    # 以前は (0, 0, 0, 1) を足していたため、拭いた跡（0,0,0,0）が黒く濁っていきました。
    # 今回は (255, 255, 255, 1) を足します。
    # これにより、透明な部分が一瞬で「白い色」を取り戻しつつ、Alphaだけが1ずつ増えます。
    fog_adder = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    fog_adder.fill((255, 255, 255, 1))

    # 3. 上限キャップ用レイヤー
    # これ以上濃くならない（白くなりすぎない）ための蓋
    fog_limit = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    fog_limit.fill((*FOG_COLOR, FOG_MAX_ALPHA))

    # 4. 指ブラシ（透明にする）
    wiper_brush = pygame.Surface((WIPE_RADIUS * 2, WIPE_RADIUS * 2), pygame.SRCALPHA)
    # ブラシの外側は白（保存）
    wiper_brush.fill((255, 255, 255, 255))
    # ブラシの内側は透明（削除: 0,0,0,0）
    pygame.draw.circle(
        wiper_brush, (0, 0, 0, 0), (WIPE_RADIUS, WIPE_RADIUS), WIPE_RADIUS
    )

    regen_counter = 0.0

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # --- 1. 内側の処理（指で曇りを拭く） ---
        if pygame.mouse.get_pressed()[0]:
            mx, my = pygame.mouse.get_pos()
            # 結露レイヤーだけを透明にする (Alpha=0, RGB=0 になる)
            fog_surface.blit(
                wiper_brush,
                (mx - WIPE_RADIUS, my - WIPE_RADIUS),
                special_flags=pygame.BLEND_RGBA_MIN,
            )

        # --- 2. 曇りの超スロー再生（白く戻す） ---
        regen_counter += FOG_REGEN_SPEED
        if regen_counter >= 1.0:
            # A. 全体に「白 + Alpha1」を足す
            # 拭いた跡 (0,0,0,0) + (255,255,255,1) = (255,255,255,1) -> うっすら白い霧が出現
            fog_surface.blit(fog_adder, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

            # B. 上限カット（初期状態より濃くしない）
            fog_surface.blit(fog_limit, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

            regen_counter = 0.0

        # --- 3. 外側の処理（雨粒） ---

        # 静止水滴の付着
        if len(static_drops) < STATIC_DROP_COUNT:
            for _ in range(SPAWN_SPEED):
                static_drops.append(
                    [
                        random.randint(0, WIDTH),
                        random.randint(0, HEIGHT),
                        random.randint(1, 3),
                    ]
                )

        # 落ちてくる雨粒
        if random.randint(0, 100) < 4:
            falling_drops.append(
                FallingDrop(random.randint(0, WIDTH), random.uniform(4, 7))
            )

        # 雨粒の更新と巻き込み
        for f_drop in falling_drops:
            f_drop.update()

            limit_dist_sq = (f_drop.r + 5) ** 2

            # 外側の静止水滴だけを消す
            static_drops = [
                s
                for s in static_drops
                if not (
                    abs(s[0] - f_drop.x) < f_drop.r + 5
                    and abs(s[1] - f_drop.y) < f_drop.r + 5
                    and (s[0] - f_drop.x) ** 2 + (s[1] - f_drop.y) ** 2 < limit_dist_sq
                )
            ]

        falling_drops = [f for f in falling_drops if not f.to_remove]

        # --- 描画 ---

        # Layer 1: 背景
        screen.blit(background, (0, 0))

        # Layer 2: 外側の静止水滴
        for s in static_drops:
            pygame.draw.circle(screen, STATIC_DROP_COLOR, (s[0], s[1]), s[2])

        # Layer 3: 外側の落ちてくる雨粒
        for f in falling_drops:
            f.draw(screen)

        # Layer 4: 内側の結露（一番手前）
        screen.blit(fog_surface, (0, 0))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
