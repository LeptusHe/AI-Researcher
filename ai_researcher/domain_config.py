# Domain configuration for Mobile Graphics / Real-time Rendering / Game Engine Optimization

DOMAIN_NAME = "Mobile Graphics, Real-time Rendering, and Game Engine Optimization"

DOMAIN_SHORT = "mobile graphics and real-time rendering"

TARGET_CONFERENCES = [
    "SIGGRAPH",
    "SIGGRAPH Asia",
    "Eurographics (EG)",
    "I3D (Symposium on Interactive 3D Graphics and Games)",
    "HPG (High-Performance Graphics)",
    "MobiSys",
    "MobiCom",
]

TARGET_CONFERENCES_SHORT = "SIGGRAPH and Eurographics"

RESEARCH_SUBDIRECTIONS = [
    "mobile real-time rendering",
    "shader optimization for mobile GPUs",
    "LOD and scene management for mobile",
    "texture compression and streaming",
    "neural rendering on mobile devices",
    "frame rate and latency optimization",
    "Vulkan/Metal graphics API optimization",
    "energy-efficient rendering",
    "temporal antialiasing and upsampling on mobile",
    "GPU-driven rendering pipelines for mobile",
]

# Method types (replacing prompting/finetuning)
METHOD_TYPES = {
    "rendering_optimization": "rendering_optimization",
    "neural_graphics": "neural_graphics",
    "engine_architecture": "engine_architecture",
}

METHOD_RENDERING_OPTIMIZATION = "rendering_optimization"
METHOD_NEURAL_GRAPHICS = "neural_graphics"
METHOD_ENGINE_ARCHITECTURE = "engine_architecture"

# Resource constraints
RESOURCE_CONSTRAINTS = (
    "mobile GPUs (Adreno, Mali, Apple GPU), limited VRAM and memory bandwidth, "
    "strict power and thermal budgets"
)

# Reviewer role description
REVIEWER_ROLE = (
    "You are a reviewer specialized in Mobile Graphics, Real-time Rendering, "
    "and Game Engine Optimization."
)

# Professor role description
PROFESSOR_ROLE = (
    "You are a professor specialized in Mobile Graphics, Real-time Rendering, "
    "and Game Engine Optimization."
)

# Expert researcher role
EXPERT_ROLE = (
    "You are an expert researcher in mobile graphics and real-time rendering."
)

# Example topics for scripts
EXAMPLE_TOPICS = [
    "novel real-time rendering techniques for mobile GPUs with limited bandwidth and compute",
    "energy-efficient temporal antialiasing and upsampling algorithms for mobile devices with constrained power budgets",
    "neural rendering methods optimized for deployment on mobile devices",
    "game engine optimization techniques for achieving stable 60fps on mobile platforms",
]

# Default topic
DEFAULT_TOPIC = (
    "novel real-time rendering techniques for mobile GPUs with limited bandwidth and compute"
)

# Quality metrics for graphics research
QUALITY_METRICS = [
    "PSNR",
    "SSIM",
    "LPIPS",
    "frame rate (FPS)",
    "frame time (ms)",
    "power consumption (mW)",
    "GPU memory usage (MB)",
    "draw call count",
    "triangle throughput",
]
