import os
import sys
import shutil
import subprocess
from pathlib import Path


def convert_png_to_icns(png_path):
    """Convert PNG to ICNS format for macOS"""
    # Create iconset directory
    iconset_dir = "icon.iconset"
    if os.path.exists(iconset_dir):
        shutil.rmtree(iconset_dir)
    os.makedirs(iconset_dir)

    # Generate different icon sizes
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    for size in sizes:
        # Normal resolution
        subprocess.run(
            [
                "sips",
                "-z",
                str(size),
                str(size),
                png_path,
                "--out",
                f"{iconset_dir}/icon_{size}x{size}.png",
            ],
            check=True,
        )
        # Retina resolution
        subprocess.run(
            [
                "sips",
                "-z",
                str(size * 2),
                str(size * 2),
                png_path,
                "--out",
                f"{iconset_dir}/icon_{size}x{size}@2x.png",
            ],
            check=True,
        )

    # Convert iconset to icns
    icns_path = "icon.icns"
    if os.path.exists(icns_path):
        os.remove(icns_path)
    subprocess.run(["iconutil", "-c", "icns", iconset_dir], check=True)

    # Clean up iconset directory
    shutil.rmtree(iconset_dir)
    return icns_path


def clean_build_dirs():
    """Clean build and dist directories"""
    dirs_to_clean = ["build", "dist"]
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Removing {dir_name} directory...")
            shutil.rmtree(dir_name)
    if os.path.exists("ScreenGPT.spec"):
        print("Removing ScreenGPT.spec...")
        os.remove("ScreenGPT.spec")


def create_executable():
    """Create executable using PyInstaller"""
    # Get the absolute path to the project root
    project_root = Path(__file__).parent.absolute()
    print(f"Project root: {project_root}")

    # Convert PNG to ICNS if needed
    icon_path = "assets/screen-gpt.png"
    if os.path.exists(icon_path):
        print("\nConverting PNG to ICNS format...")
        icns_path = convert_png_to_icns(icon_path)
        print(f"Created ICNS file: {icns_path}")
    else:
        print("Warning: Icon file not found. Building without custom icon.")
        icns_path = None

    # Define base PyInstaller command
    pyinstaller_cmd = [
        "pyinstaller",
        "--name=ScreenGPT",
        "--windowed",  # No console window
        "--hidden-import=torch",
        "--hidden-import=torchvision",
        "--hidden-import=transformers",
        "--hidden-import=easyocr",
        "--hidden-import=openai",
        "--hidden-import=pyttsx3",
        "--hidden-import=PIL",
        "--hidden-import=cv2",
        "--hidden-import=numpy",
        "--noconfirm",  # Replace existing build
        "--clean",  # Clean PyInstaller cache
        "--debug=all",  # Enable all debug logging
        "--log-level=DEBUG",  # Set log level to DEBUG
        "main.py",  # Entry point
    ]

    # Add icon if it exists
    if icns_path:
        pyinstaller_cmd.insert(2, f"--icon={icns_path}")

    # Add .env.example if it exists
    env_example = ".env.example"
    if os.path.exists(env_example):
        pyinstaller_cmd.insert(2, f"--add-data={env_example}:.")
    else:
        print(
            "Warning: .env.example not found. Building without example environment file."
        )

    print("\nRunning PyInstaller with command:")
    print(" ".join(pyinstaller_cmd))
    print("\n")

    # Run PyInstaller
    try:
        subprocess.run(pyinstaller_cmd, check=True)

        # Verify the build
        dist_path = Path("dist/ScreenGPT")
        if not dist_path.exists():
            print(f"Error: {dist_path} does not exist after build")
            sys.exit(1)

        print("\nBuild contents:")
        for item in dist_path.rglob("*"):
            print(f"  {item.relative_to(dist_path)}")

        # Create a debug wrapper script
        debug_script = """
import sys
import traceback
import os

try:
    from main import main
    main()
except Exception as e:
    with open('error.log', 'w') as f:
        f.write(f'Error: {str(e)}\\n')
        f.write('\\nTraceback:\\n')
        traceback.print_exc(file=f)
    print(f'Error occurred. Check error.log for details.')
    input('Press Enter to exit...')
"""
        with open("debug_wrapper.py", "w") as f:
            f.write(debug_script)

        # Clean up ICNS file if it was created
        if icns_path and os.path.exists(icns_path):
            os.remove(icns_path)

    except subprocess.CalledProcessError as e:
        print(f"Error during build: {e}")
        sys.exit(1)


def main():
    print("Starting build process...")
    print(f"Current working directory: {os.getcwd()}")

    # Clean previous builds
    print("\nCleaning previous builds...")
    clean_build_dirs()

    # Create executable
    print("\nCreating executable...")
    create_executable()

    print("\nBuild completed successfully!")
    print("Executable can be found in the 'dist/ScreenGPT' directory")


if __name__ == "__main__":
    main()
