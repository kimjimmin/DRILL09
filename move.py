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
