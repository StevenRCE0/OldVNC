#!/bin/bash
dev=$1 # 需要修改成自己的设备 id, 使用 adb devices 获取
img=/sdcard/capture.png
save_image_path=/sdcard/DCIM/Old

adb(){
    /opt/homebrew/bin/adb -s $dev $@
}

push(){
    # adb push loop.js /sdcard/Scripts/loop.js 
    # adb shell am start -n org.autojs.autojs/.external.open.RunIntentActivity -d /sdcard/Scripts/loop.js
    # check if save_image_path exists, if not, create it
    adb shell mkdir -p $save_image_path
}

cleanup(){
    adb shell rm $img
    rm $snapshot
}

text(){
    adb shell input text $1
}

unlock(){
    adb shell input keyevent 224 # 唤醒设备
    # adb shell input swipe 300 500 300 1500 # 上滑到密码输入界面
    # adb shell input text password # 需要修改成自己的锁屏密码
}

tap(){
    x=$1
    y=$2
    adb shell input tap $x $y
}

screenshoot(){
    #  sleep 3
    adb shell screencap -p $img
    adb pull $img $1
}

save_image(){
    adb push $1 $save_image_path
}

# read parameter and run
case $2 in
    cleanup)
        cleanup
        ;;
    unlock)
        unlock
        ;;
    screenshoot)
        screenshoot $3
        ;;
    tap)
        tap $3 $4
        ;;
    text)
        text $3
        ;;
    push)
        push
        ;;
    save_image)
        save_image $3
        ;;
    *)
        echo "Usage: $0 {device} {cleanup|unlock|screenshoot|tap|text|push|save_image}"
        exit 1
        ;;
esac