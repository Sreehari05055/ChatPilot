import os
from app import logger
import psutil

try:
    import torch
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False

class HardwareDetector:
    @staticmethod
    def get_gpu_info():
        if not _TORCH_AVAILABLE:
            return False, 0, "None (Torch not installed)"
        if torch.cuda.is_available():
            try:
                device_id = torch.cuda.current_device()
                props = torch.cuda.get_device_properties(device_id)
                vram_gb = props.total_memory / (1024**3)
                return True, vram_gb, props.name
            except Exception:
                return False, 0, "Error detecting GPU"
        return False, 0, "None"

    @staticmethod
    def get_cpu_info():
        return psutil.virtual_memory().total / (1024**3)

    @staticmethod
    def should_use_acceleration(min_vram_gb=2.0, min_total_ram_gb=8.0):
        has_gpu, vram, gpu_name = HardwareDetector.get_gpu_info()
        if has_gpu and vram >= min_vram_gb:
            return True, "GPU (CUDA)"
        return False, "CPU"

    @staticmethod
    def get_runtime_config():
        """
        Returns hardware-specific configuration to be injected into Docling pipelines.
        """
        from docling.datamodel.pipeline_options import AcceleratorOptions, AcceleratorDevice
        from app.core.config import Config

        device = AcceleratorDevice.CUDA if Config.USE_GPU_ACCELERATION else AcceleratorDevice.AUTO
        
        accel_options = AcceleratorOptions(
            device=device,
            num_threads=Config.CPU_COUNT
        )

        # Batch sizes are only relevant for High-Performance GPU mode
        batch_sizes = {}
        if Config.USE_GPU_ACCELERATION:
            batch_sizes = {
                "ocr_batch_size": 4,
                "layout_batch_size": 64,
                "table_batch_size": 4
            }
            
        return {
            "accelerator_options": accel_options,
            "batch_sizes": batch_sizes
        }
