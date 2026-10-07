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
