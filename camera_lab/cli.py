from __future__ import annotations

import argparse

from .io_utils import load_image_rgb, save_image_rgb
from .pipeline import process_image
from .profile import CameraProfile


def main():
    ap = argparse.ArgumentParser(description="Mini Camera Lab batch processor")
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--profile", help="Camera profile JSON")
    args = ap.parse_args()

    profile = CameraProfile.load(args.profile) if args.profile else CameraProfile()
    image = load_image_rgb(args.input)
    stages = process_image(image, profile)
    save_image_rgb(args.output, stages["final"])
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
