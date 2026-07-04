# build/app/android_so.py
#
# Собирает libXray под Android как c-shared (.so) или c-archive (.a) с C-ABI
# экспортами CGo* — то, что можно линковать в Rust (в отличие от gomobile AAR,
# где symbols это JNI Java_...).
#
# Использует ту же машинерию, что LinuxBuilder: prepare_static_lib() кладёт
# main.gotemplate -> main.go и переименовывает `package libXray` -> `package main`,
# reset_files() возвращает всё назад после сборки.
#
# Запуск (после правки main.py, см. ниже), из корня репозитория:
#   ANDROID_NDK_HOME=/path/to/ndk python3 build/main.py android-so            # .so
#   ANDROID_NDK_HOME=/path/to/ndk python3 build/main.py android-so c-archive  # .a
#
# Результат: <repo>/android_out/<abi>/libXray.{so,a} (+ libXray.h)

import os
import subprocess

from app.build import Builder
from app.cmd import create_dir_if_not_exists, delete_dir_if_exists


class AndroidSoBuilder(Builder):
    # Android ABI -> (GOARCH, GOARM, NDK clang prefix)
    ABIS = {
        "arm64-v8a":   ("arm64", None, "aarch64-linux-android"),
        "armeabi-v7a": ("arm",   "7",  "armv7a-linux-androideabi"),
        "x86_64":      ("amd64", None, "x86_64-linux-android"),
        "x86":         ("386",   None, "i686-linux-android"),
    }

    def __init__(self, build_dir, use_local_xray_core=False,
                 build_mode="c-shared", api=21):
        super().__init__(build_dir, use_local_xray_core)
        self.build_mode = build_mode           # "c-shared" -> .so, "c-archive" -> .a
        self.api = api
        self.lib_ext = "so" if build_mode == "c-shared" else "a"
        self.out_dir = os.path.join(self.lib_dir, "android_out")
        delete_dir_if_exists(self.out_dir)
        create_dir_if_not_exists(self.out_dir)

    def before_build(self):
        super().before_build()
        # main.gotemplate (//export CGo*) + package main
        self.prepare_static_lib()

    def build(self):
        self.before_build()

        ndk = os.environ["NDK_HOME"]
        host = "darwin-x86_64" if os.uname().sysname == "Darwin" else "linux-x86_64"
        toolchain = os.path.join(ndk, "toolchains", "llvm", "prebuilt", host, "bin")

        for abi, (goarch, goarm, prefix) in self.ABIS.items():
            out_abi = os.path.join(self.out_dir, abi)
            create_dir_if_not_exists(out_abi)
            out_file = os.path.join(out_abi, f"libXray.{self.lib_ext}")
            cc = os.path.join(toolchain, f"{prefix}{self.api}-clang")

            env = os.environ.copy()
            env["GOOS"] = "android"
            env["GOARCH"] = goarch
            if goarm:
                env["GOARM"] = goarm
            env["CGO_ENABLED"] = "1"
            env["CC"] = cc

            cmd = [
                "go", "build", "-trimpath",
                # -checklinkname=0: xray-core тянет //go:linkname в стдлиб,
                #   без этого свежий Go откажется линковать.
                # max-page-size=16384: требование Android 15 (16 KB страницы).
                "-ldflags",
                "-s -w -checklinkname=0 -extldflags=-Wl,-z,max-page-size=16384",
                f"-o={out_file}",
                f"-buildmode={self.build_mode}",
            ]
            os.chdir(self.lib_dir)
            print(f"[{abi}] CC={cc}")
            print(cmd)
            ret = subprocess.run(cmd, env=env)
            if ret.returncode != 0:
                raise Exception(f"android build failed for {abi}")

        self.after_build()
        self.revert_go_env()

    def after_build(self):
        super().after_build()
        self.reset_files()   # убрать main.go, вернуть package libXray
