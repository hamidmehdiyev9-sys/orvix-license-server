"""GPU / OpenCV sürətləndirmə."""
import numpy as np
import cv2

class GPUAccelerator:
    def __init__(self):
        self.use_cuda = False
        self.use_opencl = False
        self.umat_enabled = False
        self.gpu_name = "CPU"
        self.gpu_type = "CPU"
        self.umat_available = False
        self._detect_gpu()

    def _detect_gpu(self):
        try:
            test_umat = cv2.UMat(10, 10, cv2.CV_8UC3)
            if test_umat is not None:
                self.umat_available = True
        except Exception:
            pass
        try:
            if hasattr(cv2, 'cuda'):
                cuda_count = cv2.cuda.getCudaEnabledDeviceCount()
                if cuda_count > 0:
                    self.use_cuda = True
                    self.gpu_type = "NVIDIA"
                    cv2.cuda.setDevice(0)
                    device_info = cv2.cuda.DeviceInfo()
                    self.gpu_name = device_info.name()
                    self.umat_enabled = True
        except Exception:
            pass
        if not self.use_cuda:
            try:
                if cv2.ocl.haveOpenCL():
                    cv2.ocl.setUseOpenCL(True)
                    if cv2.ocl.useOpenCL():
                        self.use_opencl = True
                        device_name = cv2.ocl.Device.getDefault().name().lower()
                        if 'nvidia' in device_name:
                            self.gpu_type = "NVIDIA"
                        elif 'amd' in device_name:
                            self.gpu_type = "AMD"
                        elif 'intel' in device_name:
                            self.gpu_type = "INTEL"
                        else:
                            self.gpu_type = "OPENCL"
                        self.gpu_name = cv2.ocl.Device.getDefault().name()
                        self.umat_enabled = True
            except Exception:
                pass
        if self.umat_available and not self.use_cuda and not self.use_opencl:
            self.umat_enabled = True
            self.gpu_type = "UMAT"
            self.gpu_name = "UMAT Mode"
        if not self.use_cuda and not self.use_opencl and not self.umat_enabled:
            self.gpu_type = "CPU"
            self.gpu_name = "CPU"
        if self.use_opencl or self.umat_enabled:
            try:
                cv2.ocl.setUseOpenCL(True)
            except Exception:
                pass

    def to_gray(self, frame):
        if self.use_cuda:
            try:
                gpu_frame = cv2.cuda_GpuMat()
                gpu_frame.upload(frame)
                gpu_gray = cv2.cuda.cvtColor(gpu_frame, cv2.COLOR_RGB2GRAY)
                return gpu_gray.download()
            except Exception:
                pass
        if self.umat_enabled:
            try:
                gpu_frame = cv2.UMat(frame)
                gpu_gray = cv2.cvtColor(gpu_frame, cv2.COLOR_RGB2GRAY)
                return gpu_gray.get()
            except Exception:
                pass
        return cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

    def frame_diff(self, frame1, frame2):
        if self.use_cuda:
            try:
                gpu_f1 = cv2.cuda_GpuMat()
                gpu_f2 = cv2.cuda_GpuMat()
                gpu_f1.upload(frame1)
                gpu_f2.upload(frame2)
                gpu_diff = cv2.cuda.absdiff(gpu_f1, gpu_f2)
                diff_sum = cv2.cuda.sum(gpu_diff).download()[0]
                return diff_sum / (frame1.shape[0] * frame1.shape[1] * 3)
            except Exception:
                pass
        if self.umat_enabled:
            try:
                gpu_f1 = cv2.UMat(frame1)
                gpu_f2 = cv2.UMat(frame2)
                gpu_diff = cv2.absdiff(gpu_f1, gpu_f2)
                diff = gpu_diff.get()
                return np.mean(np.abs(diff.astype(np.int16)))
            except Exception:
                pass
        return np.mean(np.abs(frame1.astype(np.int16) - frame2.astype(np.int16)))

    def get_gpu_info(self):
        return {'type': self.gpu_type, 'name': self.gpu_name, 'mode': 'MAX SPEED'}


gpu_acc = GPUAccelerator()
