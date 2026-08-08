# 授权与激活

在 `license_manager.py` 中将 `LICENSE_ENFORCEMENT_ENABLED = True` 后，软件首次可联网运行时会记录试用开始日；试用共 30 个自然日。每次启动和每五分钟都会通过 HTTPS `Date` 响应同步时间。试用或授权到期、系统时间回退、或无法联网校时，翻译 API 与界面操作都会被锁定；用户仍可在激活页输入新码。默认值为 `False`，完全跳过联网校时和授权限制，适合不能作商业分发的 ODA 构建。

激活码包含可解码的到期日期和套餐名，并由 Ed25519 私钥签名。客户端仅包含公钥，不能自行生成有效激活码。

私钥已在首次配置时保存在项目外的 `Documents/HonsenCADLicenseIssuer/license_private_key.pem`。不要把它提交到 Git、复制给客户或随 EXE 分发。

签发激活码：

```powershell
python license_issuer.py issue --private-key "$env:USERPROFILE\Documents\HonsenCADLicenseIssuer\license_private_key.pem" --expires-on 2027-08-08 --plan "一年版"
```

命令输出的一整行即激活码。`--expires-on` 可填任意日期，因此不同套餐只需使用不同的到期日与 `--plan` 文案。客户在启动页输入后立即生效。

如需迁移签发环境，安全复制该私钥；若丢失，只能生成新密钥、更新客户端公钥并重新打包，旧激活码会随之失效。

## 赞助收款码

收费开关关闭时，标题栏的“赞助作者”会读取 `license_manager.py` 内的 `SUPPORT_WECHAT_QR_URL` 和 `SUPPORT_ALIPAY_QR_URL`。推荐使用 Cloudflare R2 绑定自己的域名，例如：

```python
SUPPORT_WECHAT_QR_URL = "https://assets.example.com/honsen-cad/wechat.png"
SUPPORT_ALIPAY_QR_URL = "https://assets.example.com/honsen-cad/alipay.png"
```

将新二维码上传为相同 object key 即可保持 URL 不变；若该自定义域名启用 CDN 缓存，替换后清除该 URL 的缓存或设置短 TTL。收费开关开启时，同一位置改为“购买许可”，显示当前试用或授权的到期日与套餐。

“购买许可”始终提供激活码输入框；即使当前授权还未到期，也可输入新码续期。授权开启且没有有效试用/许可时，启动会直接打开该窗口、阻止全部主体操作；关闭窗口会退出桌面程序，只有成功激活才解除限制。

当前构建使用 Gitee 的固定 raw 链接 `qr_wx.jpg` 与 `qr_ali.jpg`；实测返回 `image/jpeg`，缓存时间为 60 秒，因此覆盖同名文件后通常一分钟内生效。软件启动时会后台下载它们到用户目录的 `.cad_translator_qr_cache/wechat.bin` 与 `alipay.bin`，仅保存二进制内容而非图片文件；本地缓存每 7 天刷新一次，弹窗始终优先读取本地缓存。
