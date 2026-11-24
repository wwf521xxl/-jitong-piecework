# 计件通 · 安卓员工版

这是给员工用的安卓 APK，只做：

- 首次设置服务器 IP；
- 工号 + PIN 登录；
- 大按钮“扫码报工”；
- 原生相机扫码；
- 调用服务端自动报工接口；
- 报工成功页；
- 手动输入订单号兜底。

## 重要

Android Gradle 不支持中文项目路径。  
请把整个 `android-app` 目录复制到英文路径再构建，例如：

```text
D:\jitong-android
```

## 构建

环境：

- JDK 17+
- Android SDK Platform 35
- Build-Tools 35.0.0
- Gradle 8.10.2

命令：

```powershell
cd D:\jitong-android
$env:ANDROID_HOME="D:\Android\sdk"
$env:JAVA_HOME="D:\ps"
D:\Android\gradle-dist\gradle-8.10.2\bin\gradle.bat assembleRelease
```

输出：

```text
app\build\outputs\apk\release\app-release.apk
```

## 签名

正式 APK 使用 `jitong-release.jks` 签名。  
升级 APK 必须继续使用同一个 keystore，否则不能覆盖安装。

不要把 `jitong-release.jks` 和 `keystore.properties` 发给客户。

## 服务器要求

- 计件通服务器已启动；
- 8443 和 8788 端口可访问；
- 手机和服务器在同一 Wi-Fi；
- 服务器证书包含服务器局域网 IP。

App 会通过：

```text
http://服务器IP:8788/jitong-local-ca.cer
```

下载根证书并在 App 内部信任，所以**手机系统不需要安装证书**。

## 客户安装

1. 安装 `jitong-worker.apk`；
2. 允许未知来源；
3. 首次输入服务器 IP；
4. 工号 + PIN 登录；
5. 以后点图标 → 扫码报工。
