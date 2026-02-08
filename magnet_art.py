import pygame
import math

# --- 設定パラメータ ---
WIDTH, HEIGHT = 800, 600
BG_COLOR = (255, 255, 255)

# 色定義
COLOR_N = (220, 60, 60)  # N極（赤）
COLOR_S = (60, 60, 220)  # S極（青）
TEXT_COLOR = (255, 255, 255)
BORDER_COLOR = (150, 150, 150)

# 物理定数
MAGNET_FORCE = 2500.0  # 磁力
MAX_FORCE = 15.0  # 力の上限
FRICTION = 0.70  # 摩擦（止まりやすくする）
SUB_STEPS = 10  # 計算精度


class Pole:
    def __init__(self, polarity):
        self.polarity = polarity  # 1=N, -1=S
        self.rel_x = 0  # 中心からの相対座標（回転によって変わる）
        self.rel_y = 0

    def update_pos(self, w, h, angle):
        """回転角に応じて極の位置を計算する"""
        # 基本：左がS, 右がN (angle=0)
        # angleは 0, 90, 180, 270
        offset = max(w, h) / 2 - 2  # 端っこ

        if angle == 0:  # 横向き (S-N)
            self.rel_x = offset * self.polarity  # N(1)は右, S(-1)は左
            self.rel_y = 0
        elif angle == 90:  # 縦向き (S上-N下) -> 時計回り90度
            self.rel_x = 0
            self.rel_y = offset * self.polarity  # N下, S上
        elif angle == 180:  # 横向き逆 (N-S)
            self.rel_x = -offset * self.polarity  # N左, S右
            self.rel_y = 0
        elif angle == 270:  # 縦向き逆 (N上-S下)
            self.rel_x = 0
            self.rel_y = -offset * self.polarity

    def get_world_pos(self, cx, cy):
        return cx + self.rel_x, cy + self.rel_y


class BarMagnet:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0

        # 基本サイズ
        self.base_w = 140
        self.base_h = 40

        # 現在のサイズ（回転で入れ替わる）
        self.width = self.base_w
        self.height = self.base_h

        self.mass = 2.0
        self.angle = 0  # 0, 90, 180, 270

        # 磁極
        self.poles = [Pole(-1), Pole(1)]  # S, N
        self.update_geometry()  # 初期化

        self.is_dragging = False
        self.drag_mode = 0  # 1=Left, 3=Right

    def rotate(self, direction):
        """90度回転させる (direction: 1=Right, -1=Left)"""
        self.angle += direction * 90
        self.angle %= 360
        self.update_geometry()

    def update_geometry(self):
        """角度に基づいて幅/高さと極の位置を更新"""
        if self.angle == 0 or self.angle == 180:
            self.width = self.base_w
            self.height = self.base_h
        else:
            self.width = self.base_h
            self.height = self.base_w

        for p in self.poles:
            p.update_pos(self.width, self.height, self.angle)

    def apply_force(self, fx, fy):
        if not self.is_dragging:
            self.vx += fx / self.mass
            self.vy += fy / self.mass

    def update_physics(self):
        if self.is_dragging:
            self.vx = 0
            self.vy = 0
            return

        self.vx *= FRICTION
        self.vy *= FRICTION

        if abs(self.vx) < 0.05:
            self.vx = 0
        if abs(self.vy) < 0.05:
            self.vy = 0

        self.x += self.vx
        self.y += self.vy

        self.x = max(self.width / 2, min(WIDTH - self.width / 2, self.x))
        self.y = max(self.height / 2, min(HEIGHT - self.height / 2, self.y))

    def get_rect(self):
        return pygame.Rect(
            self.x - self.width / 2, self.y - self.height / 2, self.width, self.height
        )

    def draw(self, screen, font):
        rect = self.get_rect()

        # 角度に応じて描画色を塗り分ける
        # N極エリアとS極エリアを計算

        cx, cy = rect.centerx, rect.centery
        w, h = rect.width, rect.height

        rect_n = None
        rect_s = None

        if self.angle == 0:  # S(左) N(右)
            rect_s = pygame.Rect(rect.x, rect.y, w / 2, h)
            rect_n = pygame.Rect(rect.x + w / 2, rect.y, w / 2, h)
        elif self.angle == 90:  # S(上) N(下)
            rect_s = pygame.Rect(rect.x, rect.y, w, h / 2)
            rect_n = pygame.Rect(rect.x, rect.y + h / 2, w, h / 2)
        elif self.angle == 180:  # N(左) S(右)
            rect_n = pygame.Rect(rect.x, rect.y, w / 2, h)
            rect_s = pygame.Rect(rect.x + w / 2, rect.y, w / 2, h)
        elif self.angle == 270:  # N(上) S(下)
            rect_n = pygame.Rect(rect.x, rect.y, w, h / 2)
            rect_s = pygame.Rect(rect.x, rect.y + h / 2, w, h / 2)

        pygame.draw.rect(screen, COLOR_S, rect_s)
        pygame.draw.rect(screen, COLOR_N, rect_n)

        # 枠線
        pygame.draw.rect(screen, BORDER_COLOR, rect, width=1)

        # 強制モード枠
        if self.is_dragging and self.drag_mode == 3:
            pygame.draw.rect(screen, (255, 200, 0), rect, width=3)

        # 文字（回転に合わせて描画位置調整）
        s_surf = font.render("S", True, TEXT_COLOR)
        n_surf = font.render("N", True, TEXT_COLOR)

        # 中心から少しずらして配置
        # ポール情報を使えば正確
        for p in self.poles:
            txt = n_surf if p.polarity == 1 else s_surf
            tx = cx + p.rel_x * 0.8  # 少し中心寄り
            ty = cy + p.rel_y * 0.8
            screen.blit(txt, (tx - txt.get_width() / 2, ty - txt.get_height() / 2))


# --- 物理エンジン ---


def solve_magnetism(magnets):
    for i in range(len(magnets)):
        mag1 = magnets[i]
        for j in range(i + 1, len(magnets)):
            mag2 = magnets[j]

            # 右クリック無視
            if (mag1.is_dragging and mag1.drag_mode == 3) or (
                mag2.is_dragging and mag2.drag_mode == 3
            ):
                continue

            for p1 in mag1.poles:
                p1_pos = p1.get_world_pos(mag1.x, mag1.y)
                for p2 in mag2.poles:
                    p2_pos = p2.get_world_pos(mag2.x, mag2.y)

                    dx = p2_pos[0] - p1_pos[0]
                    dy = p2_pos[1] - p1_pos[1]
                    dist_sq = dx * dx + dy * dy
                    if dist_sq < 4.0:
                        dist_sq = 4.0  # ガード
                    dist = math.sqrt(dist_sq)

                    force = MAGNET_FORCE / dist_sq
                    force = min(force, MAX_FORCE)

                    if p1.polarity == p2.polarity:
                        force *= -1.0  # 同極反発

                    fx = (dx / dist) * force
                    fy = (dy / dist) * force

                    mag1.apply_force(fx, fy)
                    mag2.apply_force(-fx, -fy)


def solve_collisions(magnets):
    """矩形衝突判定（回転後もAABBとして処理可能）"""
    for i in range(len(magnets)):
        for j in range(i + 1, len(magnets)):
            m1 = magnets[i]
            m2 = magnets[j]

            dx = m2.x - m1.x
            dy = m2.y - m1.y

            # 現在のサイズ（回転適用済み）で判定
            min_dist_x = (m1.width + m2.width) / 2
            min_dist_y = (m1.height + m2.height) / 2

            overlap_x = min_dist_x - abs(dx)
            overlap_y = min_dist_y - abs(dy)

            if overlap_x > 0 and overlap_y > 0:
                nx, ny = 0, 0
                if overlap_x < overlap_y:
                    nx = -1 if dx < 0 else 1
                    overlap = overlap_x
                else:
                    ny = -1 if dy < 0 else 1
                    overlap = overlap_y

                total_mass = m1.mass + m2.mass
                r1 = m2.mass / total_mass
                r2 = m1.mass / total_mass

                # 位置補正（隙間ゼロ）
                epsilon = 0.001
                if not m1.is_dragging:
                    m1.x -= nx * (overlap * r1 + epsilon)
                    m1.y -= ny * (overlap * r2 + epsilon)
                if not m2.is_dragging:
                    m2.x += nx * (overlap * r1 + epsilon)
                    m2.y += ny * (overlap * r2 + epsilon)

                # 速度抹殺（プルプル防止）
                rvx = m2.vx - m1.vx
                rvy = m2.vy - m1.vy
                vel_normal = rvx * nx + rvy * ny

                if vel_normal < 0:
                    impulse = -vel_normal / (1 / m1.mass + 1 / m2.mass)
                    ix, iy = impulse * nx, impulse * ny

                    if not m1.is_dragging:
                        m1.vx -= ix / m1.mass
                        m1.vy -= iy / m1.mass
                    if not m2.is_dragging:
                        m2.vx += ix / m2.mass
                        m2.vy += iy / m2.mass

                    # 摩擦（横滑り防止）
                    tx, ty = -ny, nx
                    vt = rvx * tx + rvy * ty
                    f_imp = -vt * 0.2
                    if not m1.is_dragging:
                        m1.vx -= f_imp * tx / m1.mass
                        m1.vy -= f_imp * ty / m1.mass
                    if not m2.is_dragging:
                        m2.vx += f_imp * tx / m2.mass
                        m2.vy += f_imp * ty / m2.mass


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Magnetic Snap: R/L to Rotate")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 18, bold=True)

    magnets = []
    # 初期配置
    magnets.append(BarMagnet(300, 200))
    magnets.append(BarMagnet(500, 200))
    magnets.append(BarMagnet(300, 400))
    magnets.append(BarMagnet(500, 400))

    dragging_magnet = None
    offset_x, offset_y = 0, 0

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                btn = event.button
                if btn in [1, 3]:
                    for mag in reversed(magnets):
                        if mag.get_rect().collidepoint(mouse_pos):
                            dragging_magnet = mag
                            mag.is_dragging = True
                            mag.drag_mode = btn

                            mag.vx = 0
                            mag.vy = 0
                            offset_x = mag.x - mouse_pos[0]
                            offset_y = mag.y - mouse_pos[1]

                            magnets.remove(mag)
                            magnets.append(mag)
                            break

            elif event.type == pygame.MOUSEBUTTONUP:
                if dragging_magnet:
                    dragging_magnet.is_dragging = False
                    dragging_magnet.drag_mode = 0
                    dragging_magnet = None

            # --- 回転操作 (R/L) ---
            elif event.type == pygame.KEYDOWN:
                # ドラッグ中の磁石、もしくはマウスの下にある磁石を回転
                target = dragging_magnet
                if not target:
                    # ドラッグしてないならマウス下のやつを探す
                    for mag in reversed(magnets):
                        if mag.get_rect().collidepoint(mouse_pos):
                            target = mag
                            break

                if target:
                    if event.key == pygame.K_r:
                        target.rotate(-1)  # 時計回り (Right)
                    elif event.key == pygame.K_l:
                        target.rotate(1)  # 反時計回り (Left)

        # 位置更新
        if dragging_magnet:
            dragging_magnet.x = mouse_pos[0] + offset_x
            dragging_magnet.y = mouse_pos[1] + offset_y

        # 物理サブステップ
        dt = 1.0 / SUB_STEPS
        for _ in range(SUB_STEPS):
            solve_magnetism(magnets)
            for mag in magnets:
                mag.update_physics()
            solve_collisions(magnets)

        # 描画
        screen.fill(BG_COLOR)

        # ガイド
        pygame.draw.line(
            screen, (240, 240, 240), (WIDTH / 2, 0), (WIDTH / 2, HEIGHT), 2
        )
        pygame.draw.line(
            screen, (240, 240, 240), (0, HEIGHT / 2), (WIDTH, HEIGHT / 2), 2
        )

        for mag in magnets:
            mag.draw(screen, font)

        # 説明
        txt = font.render(
            "Drag: Move | R/L Key: Rotate 90deg | Right Click: Detach",
            True,
            (150, 150, 150),
        )
        screen.blit(txt, (20, HEIGHT - 30))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
