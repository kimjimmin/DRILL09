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
