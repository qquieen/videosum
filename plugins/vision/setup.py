from setuptools import setup, find_packages

setup(
    name="videosummary-vision",
    version="0.1.0",
    description="VideoSum 视觉增强插件",
    author="VideoSum Team",
    packages=find_packages(),
    install_requires=[
        "opencv-python>=4.8.0",
        "pillow>=10.0.0",
    ],
    entry_points={
        "videosummary.plugins": [
            "vision = videosummary_vision:VisionPlugin",
        ],
    },
    python_requires=">=3.10",
)
