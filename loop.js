if (!requestScreenCapture()) {
    toastLog('请求截图失败');
    exit();
}

setInterval(() => {
    captureScreen('/sdcard/capture.png');
}, 3000);
