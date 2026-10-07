"""캠퍼스 배경에서 캐릭터 이동과 애니메이션을 실행하는 게임."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

import pygame


BASE_DIR = Path(__file__).resolve().parent
BACKGROUND_PATH = BASE_DIR / "TUK_GROUND.png"
SPRITE_SHEET_PATH = BASE_DIR / "animation_sheet.png"

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 1024
SCREEN_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)
WINDOW_TITLE = "Campus Runner"
TARGET_FPS = 60
MAX_DELTA_TIME = 0.05

MOVE_SPEED = 250.0
ANIMATION_FPS = 10.0
SPRITE_COLUMNS = 8
FRAME_WIDTH = 100
FRAME_HEIGHT = 100
SHEET_MARGIN = 1


class Facing(Enum):
    """캐릭터가 마지막으로 바라본 수평 방향."""

    LEFT = auto()
    RIGHT = auto()


class PlayerState(Enum):
    """입력에 따라 전환되는 캐릭터 동작 상태."""

    IDLE = auto()
    RUN = auto()


@dataclass(frozen=True)
class AnimationSpec:
    """스프라이트 시트에서 애니메이션 한 행을 찾기 위한 정보."""

    row: int
    frame_count: int = SPRITE_COLUMNS
    fps: float = ANIMATION_FPS


ANIMATION_SPECS = {
    (PlayerState.IDLE, Facing.RIGHT): AnimationSpec(row=0),
    (PlayerState.IDLE, Facing.LEFT): AnimationSpec(row=1),
    (PlayerState.RUN, Facing.RIGHT): AnimationSpec(row=2),
    (PlayerState.RUN, Facing.LEFT): AnimationSpec(row=3),
}


def load_image(path: Path, *, use_alpha: bool = True) -> pygame.Surface:
    """이미지를 불러오고 화면 출력에 적합한 픽셀 형식으로 변환한다."""

    if not path.is_file():
        raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {path}")

    image = pygame.image.load(path)
    return image.convert_alpha() if use_alpha else image.convert()


def slice_animation_frames(
    sheet: pygame.Surface, spec: AnimationSpec
) -> list[pygame.Surface]:
    """지정한 행에서 100×100 크기의 프레임들을 복사한다."""

    frames: list[pygame.Surface] = []
    sheet_bounds = sheet.get_rect()

    for column in range(spec.frame_count):
        frame_rect = pygame.Rect(
            SHEET_MARGIN + column * FRAME_WIDTH,
            SHEET_MARGIN + spec.row * FRAME_HEIGHT,
            FRAME_WIDTH,
            FRAME_HEIGHT,
        )
        if not sheet_bounds.contains(frame_rect):
            raise ValueError(f"스프라이트 범위를 벗어난 프레임입니다: {frame_rect}")
        frames.append(sheet.subsurface(frame_rect).copy())

    return frames


class Animation:
    """경과 시간을 사용해 여러 이미지를 반복 재생한다."""

    def __init__(self, frames: list[pygame.Surface], fps: float) -> None:
        if not frames:
            raise ValueError("애니메이션에는 한 개 이상의 프레임이 필요합니다.")
        if fps <= 0:
            raise ValueError("애니메이션 FPS는 0보다 커야 합니다.")

        self.frames = frames
        self.frame_duration = 1.0 / fps
        self.frame_index = 0
        self.elapsed = 0.0

    def reset(self) -> None:
        """애니메이션을 첫 프레임부터 다시 시작한다."""

        self.frame_index = 0
        self.elapsed = 0.0

    def update(self, delta_time: float) -> None:
        """누적된 시간만큼 프레임을 진행하고 마지막에서 반복한다."""

        self.elapsed += delta_time
        while self.elapsed >= self.frame_duration:
            self.elapsed -= self.frame_duration
            self.frame_index = (self.frame_index + 1) % len(self.frames)

    @property
    def image(self) -> pygame.Surface:
        """현재 화면에 그릴 프레임을 반환한다."""

        return self.frames[self.frame_index]


class Player:
    """입력, 이동, 방향 기억과 애니메이션 상태를 관리한다."""

    def __init__(
        self,
        animations: dict[tuple[PlayerState, Facing], Animation],
        start_center: tuple[int, int],
    ) -> None:
        self.animations = animations
        self.state = PlayerState.IDLE
        self.facing = Facing.RIGHT
        self.speed = MOVE_SPEED
        self.animation_key = (self.state, self.facing)
        self.animation = self.animations[self.animation_key]

        start_rect = self.animation.image.get_rect(center=start_center)
        self.position = pygame.Vector2(start_rect.topleft)

    @staticmethod
    def _axis(positive_pressed: bool, negative_pressed: bool) -> int:
        """한 축의 반대 방향 키가 동시에 눌리면 입력을 상쇄한다."""

        return int(positive_pressed) - int(negative_pressed)

    def _read_direction(self, keys: pygame.key.ScancodeWrapper) -> pygame.Vector2:
        """방향키 입력을 읽고 유효한 좌우 방향을 기억한다."""

        horizontal = self._axis(keys[pygame.K_RIGHT], keys[pygame.K_LEFT])
        vertical = self._axis(keys[pygame.K_DOWN], keys[pygame.K_UP])

        if horizontal < 0:
            self.facing = Facing.LEFT
        elif horizontal > 0:
            self.facing = Facing.RIGHT

        return pygame.Vector2(horizontal, vertical)

    @staticmethod
    def _normalized(direction: pygame.Vector2) -> pygame.Vector2:
        """대각선 입력도 한 축 이동과 같은 속도가 되도록 보정한다."""

        if direction.length_squared() == 0:
            return direction
        return direction.normalize()

    def _select_animation(self, moving: bool) -> None:
        """이동 여부와 마지막 방향에 맞는 애니메이션으로 전환한다."""

        self.state = PlayerState.RUN if moving else PlayerState.IDLE
        next_key = (self.state, self.facing)
        if next_key == self.animation_key:
            return

        self.animation_key = next_key
        self.animation = self.animations[next_key]
        self.animation.reset()

    def _clamp_position(self, bounds: pygame.Rect) -> None:
        """캐릭터의 프레임 전체가 화면 경계 안에 머물게 한다."""

        max_x = max(bounds.left, bounds.right - self.animation.image.get_width())
        max_y = max(bounds.top, bounds.bottom - self.animation.image.get_height())
        self.position.x = min(max(self.position.x, bounds.left), max_x)
        self.position.y = min(max(self.position.y, bounds.top), max_y)

    def _move(
        self, direction: pygame.Vector2, delta_time: float, bounds: pygame.Rect
    ) -> None:
        """경과 시간에 비례해 이동한 뒤 위치를 화면 안으로 제한한다."""

        self.position += direction * self.speed * delta_time
        self._clamp_position(bounds)

    def update(
        self,
        keys: pygame.key.ScancodeWrapper,
        delta_time: float,
        bounds: pygame.Rect,
    ) -> None:
        """한 프레임의 입력, 이동, 상태, 애니메이션을 갱신한다."""

        raw_direction = self._read_direction(keys)
        moving = raw_direction.length_squared() > 0
        self._select_animation(moving)
        self._move(self._normalized(raw_direction), delta_time, bounds)
        self.animation.update(delta_time)

    @property
    def rect(self) -> pygame.Rect:
        """현재 부동소수점 위치를 화면 출력용 사각형으로 변환한다."""

        return self.animation.image.get_rect(
            topleft=(round(self.position.x), round(self.position.y))
        )

    def draw(self, surface: pygame.Surface) -> None:
        """현재 애니메이션 프레임을 지정한 화면에 그린다."""

        surface.blit(self.animation.image, self.rect)


def build_animations(
    sheet: pygame.Surface,
) -> dict[tuple[PlayerState, Facing], Animation]:
    """기획서의 네 상태에 해당하는 애니메이션 객체를 만든다."""

    return {
        key: Animation(slice_animation_frames(sheet, spec), spec.fps)
        for key, spec in ANIMATION_SPECS.items()
    }


class Game:
    """게임 창, 리소스, 루프와 플레이어를 관리한다."""

    def __init__(self) -> None:
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption(WINDOW_TITLE)
        self.clock = pygame.time.Clock()
        self.running = True

        self.background = load_image(BACKGROUND_PATH, use_alpha=False)
        self.sprite_sheet = load_image(SPRITE_SHEET_PATH)
        self.animations = build_animations(self.sprite_sheet)
        self.player = Player(self.animations, self.screen.get_rect().center)

    def _handle_events(self) -> None:
        """창 닫기 또는 ESC 입력을 받으면 게임 루프를 종료한다."""

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False

    def _update(self, delta_time: float) -> None:
        """현재 키 상태로 플레이어를 갱신한다."""

        keys = pygame.key.get_pressed()
        self.player.update(keys, delta_time, self.screen.get_rect())

    def _render(self) -> None:
        """배경과 캐릭터를 순서대로 그리고 화면을 갱신한다."""

        self.screen.blit(self.background, (0, 0))
        self.player.draw(self.screen)
        pygame.display.flip()

    def run(self) -> None:
        """종료 요청 전까지 입력, 갱신, 렌더링을 반복한다."""

        while self.running:
            delta_time = self.clock.tick(TARGET_FPS) / 1000.0
            self._handle_events()
            self._update(delta_time)
            self._render()
