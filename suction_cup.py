import pygame
import math
import random
import os

# --- 設定パラメータ ---
WIDTH, HEIGHT = 800, 600
BG_COLOR = (240, 245, 255)

# デザイン
COLOR_CUP = (0, 150, 200)
COLOR_HANDLE = (50, 50, 50)
COLOR_NECK = (0, 120, 180)
COLOR_VACUUM = (255, 255, 255)

# 物理パラメータ（前回の調整値を維持）
MAX_STRETCH = 240.0  # 長さ
VACUUM_LIFE = 100.0  # 耐久力
VACUUM_DECAY = 1.2  # 減る速さ
VACUUM_RECOVER = 1.5  # 回復速度
SPRING_STIFFNESS = 0.25
DAMPING = 0.85

# 音源フォルダ
SOUND_DIR = "Sounds"


class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 10
        self.alpha = 255
        self.growth = 5

    def update(self):
        self.radius += self.growth
        self.alpha -= 15
        if self.alpha < 0:
            self.alpha = 0

    def draw(self, screen):
        if self.alpha > 0:
            s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                s,
                (100, 200, 255, self.alpha),
                (self.radius, self.radius),
                self.radius,
                width=4,
            )
            screen.blit(s, (self.x - self.radius, self.y - self.radius))


class SuctionCup:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0

        self.is_stuck = False  # 張り付いているか
        self.stuck_pos = (x, y)
        self.vacuum = VACUUM_LIFE
        self.stretch_dist = 0
        self.radius_base = 40

        # ★重要：スポッといった後の「再吸着防止」フラグ
        self.waiting_for_release = False

    def update(self, mouse_pos, mouse_pressed):
        target_x, target_y = mouse_pos

        # --- 1. 再吸着防止ロックの解除チェック ---
        # スポッといった後、マウスボタンを離すまでは「くっつかないモード」
        if self.waiting_for_release:
            if not mouse_pressed:
                self.waiting_for_release = False

            # ロック中は自由に動く（バネ挙動）
            self.update_free_physics(target_x, target_y)
            return None

        # --- 2. 張り付き中の処理 (Stuck) ---
        # ★修正：ボタンを離しても剥がれないようにした
        if self.is_stuck:
            dx = target_x - self.stuck_pos[0]
            dy = target_y - self.stuck_pos[1]
            self.stretch_dist = math.hypot(dx, dy)

            # 真空度の増減
            if self.stretch_dist > 20:
                decay = (self.stretch_dist / MAX_STRETCH) * VACUUM_DECAY * 2
                self.vacuum -= decay
            else:
                self.vacuum += VACUUM_RECOVER

            self.vacuum = min(VACUUM_LIFE, self.vacuum)

            # --- 開放判定 (Pop!) ---
            if self.vacuum <= 0 or self.stretch_dist > MAX_STRETCH:
                self.is_stuck = False

                # ★ここでロックをかける
                # スポッといった瞬間、ユーザーはまだクリックしてる可能性が高いので
                # 直後に再吸着しないようにする
                self.waiting_for_release = True

                # 跳ね返り計算
                self.vx = dx * 0.45
                self.vy = dy * 0.45
                return "POP"

            return None  # まだくっついてる

        # --- 3. 吸着判定 (Stick) ---
        # ロックがかかっておらず、クリックされたら吸着
        if mouse_pressed:
            self.is_stuck = True
            self.stuck_pos = (target_x, target_y)
            self.x, self.y = target_x, target_y
            self.vacuum = VACUUM_LIFE
            self.vx, self.vy = 0, 0
            return "STICK"

        # --- 4. 自由落下・追従 (Free) ---
        self.update_free_physics(target_x, target_y)
        return None

    def update_free_physics(self, tx, ty):
        """マウスにバネでついてくる動き"""
        self.stretch_dist = 0
        self.vacuum = VACUUM_LIFE

        ax = (tx - self.x) * SPRING_STIFFNESS
        ay = (ty - self.y) * SPRING_STIFFNESS

        self.vx += ax
        self.vy += ay
        self.vx *= DAMPING
        self.vy *= DAMPING
        self.x += self.vx
        self.y += self.vy

    def draw(self, screen, mouse_pos):
        mx, my = mouse_pos
        bx, by = self.x, self.y

        if self.is_stuck:
            bx, by = self.stuck_pos

            # Neck
            width = max(5, 20 - self.stretch_dist * 0.05)
            pygame.draw.line(screen, COLOR_NECK, (bx, by), (mx, my), int(width))

            # Cup
            shake_x, shake_y = 0, 0
            if self.vacuum < 40:
                amp = (40 - self.vacuum) * 0.2
                shake_x = random.uniform(-amp, amp)
                shake_y = random.uniform(-amp, amp)

            radius = self.radius_base + 12
            s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*COLOR_CUP, 220), (radius, radius), radius)

            alpha_vacuum = int((self.vacuum / VACUUM_LIFE) * 200)
            pygame.draw.circle(
                s, (255, 255, 255, alpha_vacuum), (radius, radius), radius * 0.6
            )

            screen.blit(s, (bx - radius + shake_x, by - radius + shake_y))

        else:
            # Free state
            pygame.draw.circle(screen, COLOR_CUP, (bx, by), self.radius_base)
            pygame.draw.circle(screen, (255, 255, 255), (bx - 12, by - 12), 10)

        # Handle
        hx, hy = (mx, my) if self.is_stuck else (bx, by)
        pygame.draw.circle(screen, COLOR_HANDLE, (hx, hy), 8)


def main():
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Suction Cup: Toggle Stick & Safety Release")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 20)

    # 音源読み込み
    has_sound = False
    path_kyu = os.path.join(SOUND_DIR, "kyu.wav")
    path_pop = os.path.join(SOUND_DIR, "pop.wav")

    try:
        if os.path.exists(path_kyu) and os.path.exists(path_pop):
            sound_kyu = pygame.mixer.Sound(path_kyu)
            sound_pop = pygame.mixer.Sound(path_pop)
            sound_kyu.set_volume(0.0)
            sound_kyu.play(-1)
            has_sound = True
            print(f"Sounds loaded from {SOUND_DIR}/")
        else:
            print(f"Sound files not found in {SOUND_DIR}/")
    except Exception as e:
        print(f"Sound Error: {e}")

    cup = SuctionCup(WIDTH // 2, HEIGHT // 2)
    particles = []

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()[0]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        result = cup.update(mouse_pos, mouse_pressed)

        # 音制御
        if has_sound:
            if result == "POP":
                sound_pop.play()
                sound_kyu.set_volume(0.0)

            # ★修正：クリック有無に関わらず、張り付いていれば音を鳴らす
            elif cup.is_stuck:
                if cup.stretch_dist > 30:
                    vol = (cup.stretch_dist - 30) / (MAX_STRETCH - 30)
                    vol = min(1.0, max(0.0, vol))
                    if cup.vacuum < 40:
                        vol = 1.0
                    sound_kyu.set_volume(vol)
                else:
                    sound_kyu.set_volume(0.0)
            else:
                sound_kyu.set_volume(0.0)

        # エフェクト
        if result == "POP":
            particles.append(Particle(cup.stuck_pos[0], cup.stuck_pos[1]))
        elif result == "STICK":
            p = Particle(cup.stuck_pos[0], cup.stuck_pos[1])
            p.growth = 2
            p.radius = 30
            particles.append(p)

        particles = [p for p in particles if p.alpha > 0]
        for p in particles:
            p.update()

        # 描画
        screen.fill(BG_COLOR)

        # ガイド
        pygame.draw.line(screen, (230, 235, 245), (0, 0), (WIDTH, HEIGHT), 300)

        for p in particles:
            p.draw(screen)

        cup.draw(screen, mouse_pos)

        # ゲージ
        if cup.is_stuck:
            bar_w, bar_h = 80, 8
            gx, gy = cup.stuck_pos[0] - bar_w / 2, cup.stuck_pos[1] + 60

            pygame.draw.rect(screen, (180, 180, 180), (gx, gy, bar_w, bar_h))

            pct = max(0, cup.vacuum / VACUUM_LIFE)
            col = (255, 50, 50) if pct < 0.25 else (50, 200, 100)
            pygame.draw.rect(screen, col, (gx, gy, bar_w * pct, bar_h))

        # UI
        status = "FREE"
        if cup.is_stuck:
            status = "STUCK"
        if cup.waiting_for_release:
            status = "RELEASE MOUSE!"  # 再吸着待ち状態

        if not has_sound:
            status += " (No Sound)"

        txt = font.render(f"State: {status}", True, (100, 100, 120))
        screen.blit(txt, (20, HEIGHT - 30))

        pygame.display.flip()
        clock.tick(60)

    if has_sound:
        sound_kyu.stop()
    pygame.quit()


if __name__ == "__main__":
    main()
