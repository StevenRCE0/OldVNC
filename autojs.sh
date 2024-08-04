#!/bin/bash
dev=$1 # 需要修改成自己的设备 id, 使用 adb devices 获取
img=/sdcard/capture.jpg
save_image_path=/sdcard/DCIM/Old

adbd(){
    adb -s $dev $@
}

push(){
    # adbd push loop.js /sdcard/Scripts/loop.js 
    # adbd shell am start -n org.autojs.autojs/.external.open.RunIntentActivity -d /sdcard/Scripts/loop.js
    # check if save_image_path exists, if not, create it
    adbd shell mkdir -p $save_image_path
}

cleanup(){
    adbd shell rm $img
    rm $snapshot
}

text(){
    adbd shell input text $1
}

unlock(){
    adbd shell input keyevent 224 # 唤醒设备
    # adbd shell input swipe 300 500 300 1500 # 上滑到密码输入界面
    # adbd shell input text password # 需要修改成自己的锁屏密码
}

tap(){
    x=$1
    y=$2
    adbd shell input tap $x $y
}

screenshoot(){
    #  sleep 3
    adbd shell screencap -p $img
    adbd pull $img $1
}

save_image(){
    adbd push $1 $save_image_path
    sleep 10
    adbd shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://$save_image_path/$2
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
        save_image $3 $4
        ;;
    *)
        echo "Usage: $0 {device} {cleanup|unlock|screenshoot|tap|text|push|save_image}"
        exit 1
        ;;
esac