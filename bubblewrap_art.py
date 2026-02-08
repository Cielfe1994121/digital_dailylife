import pygame
import math
import random

# --- 設定パラメータ ---
WIDTH, HEIGHT = 800, 600
BG_COLOR = (30, 30, 35)  # 背景

# プチプチの設定
BUBBLE_RADIUS = 30  # 半径
SPACING = 70  # 間隔
COLOR_BUBBLE_BASE = (100, 150, 170)  # 通常時
COLOR_HIGHLIGHT = (255, 255, 255)  # 光沢
COLOR_STRESS = (200, 220, 255)  # 限界時
COLOR_POPPED = (60, 70, 80)  # 潰れた後

# 物理設定
POP_THRESHOLD = 1.0  # 破裂閾値
PRESSURE_SPEED = 0.04  # 押し込む速さ（少しゆっくりにして溜め感アップ）
RECOVERY_SPEED = 0.1  # 戻る速さ


class Particle:
    """弾けた時の破片"""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(2, 8)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 255
        self.size = random.randint(2, 5)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.5  # 重力
        self.life -= 15  # フェードアウト

    def draw(self, screen):
        if self.life > 0:
            s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                s, (200, 220, 255, max(0, self.life)), (self.size, self.size), self.size
            )
            screen.blit(s, (self.x - self.size, self.y - self.size))


class Bubble:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = BUBBLE_RADIUS

        self.pressure = 0.0  # 現在の圧力 (0.0 ~ 1.0)
        self.is_popped = False

        # 震え演出用
        self.shake_x = 0
        self.shake_y = 0

    def update(self, mouse_pos, mouse_pressed):
        if self.is_popped:
            return False

        # マウスとの距離
        dx = mouse_pos[0] - self.x
        dy = mouse_pos[1] - self.y
        dist = math.hypot(dx, dy)

        # 判定：マウスが乗っていて、かつ左クリックされている
        if dist < self.radius + 5 and mouse_pressed:
            # 圧力を高める
            if self.pressure < POP_THRESHOLD:
                self.pressure += PRESSURE_SPEED

                # 限界に近いと震える
                if self.pressure > 0.6:
                    shake_amount = (self.pressure - 0.6) * 8
                    self.shake_x = random.uniform(-shake_amount, shake_amount)
                    self.shake_y = random.uniform(-shake_amount, shake_amount)
            else:
                # 限界突破 -> 破裂
                self.pop()
                return True
        else:
            # 離すと圧力が戻る
            self.pressure -= RECOVERY_SPEED
            self.shake_x = 0
            self.shake_y = 0
            if self.pressure < 0:
                self.pressure = 0.0

        return False

    def pop(self):
        self.is_popped = True
        self.pressure = 0.0
        self.shake_x = 0
        self.shake_y = 0

    def draw(self, screen):
        cx = int(self.x + self.shake_x)
        cy = int(self.y + self.shake_y)

        if self.is_popped:
            # --- 潰れた状態 ---
            pygame.draw.circle(screen, COLOR_POPPED, (cx, cy), self.radius)
            # シワ
            pygame.draw.arc(
                screen, (40, 50, 60), (cx - 15, cy - 15, 30, 30), 0, 3.14, 2
            )
            pygame.draw.line(screen, (40, 50, 60), (cx - 10, cy), (cx + 10, cy + 5), 2)
        else:
            # --- 生きている状態 ---

            # 変形
            squish = self.pressure * 4

            # ★ここが修正ポイント：色の計算結果を整数(int)にする
            # floatのままだとエラーになるため変換
            base_c = tuple(
                min(255, max(0, int(c + (s - c) * self.pressure)))
                for c, s in zip(COLOR_BUBBLE_BASE, COLOR_STRESS)
            )

            # 本体
            pygame.draw.circle(screen, base_c, (cx, cy), int(self.radius + squish))

            # 影（右下）
            # 半透明を描くためにSurfaceを使う
            s_shadow = pygame.Surface(
                (self.radius * 2 + 10, self.radius * 2 + 10), pygame.SRCALPHA
            )
            pygame.draw.circle(
                s_shadow,
                (0, 0, 0, 40),
                (self.radius + 5, self.radius + 5),
                self.radius,
                width=2,
            )
            screen.blit(s_shadow, (cx - self.radius - 5, cy - self.radius - 5))

            # 凹み影（中心）
            if self.pressure > 0.1:
                shadow_radius = int(self.radius * 0.8 * self.pressure)
                if shadow_radius > 0:
                    s = pygame.Surface(
                        (shadow_radius * 2, shadow_radius * 2), pygame.SRCALPHA
                    )
                    alpha = int(100 * self.pressure)
                    pygame.draw.circle(
                        s,
                        (0, 0, 0, alpha),
                        (shadow_radius, shadow_radius),
                        shadow_radius,
                    )
                    screen.blit(s, (cx - shadow_radius, cy - shadow_radius))

            # ハイライト（光沢）
            hl_offset = 10 * (1.0 - self.pressure * 0.5)
            hl_pos_x = cx - hl_offset
            hl_pos_y = cy - hl_offset
            hl_radius = 8 + squish

            s_hl = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(s_hl, (*COLOR_HIGHLIGHT, 180), (20, 20), hl_radius)
            screen.blit(s_hl, (hl_pos_x - 20, hl_pos_y - 20))


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Bubble Wrap: Press and Hold to Pop")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 20)

    bubbles = []
    # 配置計算
    cols = int(WIDTH // SPACING)
    rows = int(HEIGHT // SPACING)

    offset_x = (WIDTH - (cols * SPACING)) / 2 + SPACING / 2
    offset_y = (HEIGHT - (rows * SPACING)) / 2 + SPACING / 2

    for r in range(rows):
        for c in range(cols):
            shift = (SPACING // 2) if r % 2 == 1 else 0
            bx = offset_x + c * SPACING + shift - (SPACING // 4 if r % 2 == 1 else 0)
            by = offset_y + r * SPACING

            # 画面内チェック
            if 0 < bx < WIDTH and 0 < by < HEIGHT:
                bubbles.append(Bubble(bx, by))

    particles = []

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()[0]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    for b in bubbles:
                        b.is_popped = False
                        b.pressure = 0

        # 更新
        for b in bubbles:
            if b.update(mouse_pos, mouse_pressed):
                # 破裂
                for _ in range(12):
                    particles.append(Particle(b.x, b.y))

        particles = [p for p in particles if p.life > 0]
        for p in particles:
            p.update()

        # 描画
        screen.fill(BG_COLOR)

        for b in bubbles:
            b.draw(screen)

        for p in particles:
            p.draw(screen)

        text = font.render("Hold Click to Squeeze / R to Reset", True, (150, 150, 150))
        screen.blit(text, (20, HEIGHT - 30))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
