<div dir="rtl">

# چطور X-OS را دانلود و امتحان کنم

> X-OS هنوز در حال توسعه است. **روی کامپیوتر اصلی‌ات نصبش نکن.**
> اول در ماشین مجازی امتحان کن، بعد با فلش در حالت «بدون نصب».

## ۱. دانلود فایل ISO

GitHub خودش ISO را می‌سازد:

1. برو به: `https://github.com/AwmiresGg/X-os/actions/workflows/build-iso.yml`
2. آخرین اجرای سبز (✓) را باز کن. (ساختن حدود ۴۰ تا ۶۰ دقیقه طول می‌کشد.)
3. پایین صفحه، بخش **Artifacts** → روی `x-os-desktop-iso` کلیک کن (باید وارد حساب GitHub باشی).
4. فایل zip را باز کن: داخلش `x-os-0.1.0-dev-desktop-amd64.iso` و فایل `.sha256` است.
5. سلامت فایل را چک کن (PowerShell):
   ```powershell
   Get-FileHash .\x-os-0.1.0-dev-desktop-amd64.iso -Algorithm SHA256
   ```
   عدد باید با محتوای فایل `.sha256` یکی باشد.

## ۲. امتحان در ماشین مجازی (امن‌ترین راه — هیچ چیزی در ویندوز عوض نمی‌شود)

1. **VirtualBox** را از `virtualbox.org` نصب کن.
2. **New** → Name: `X-OS` → ISO Image: فایل ISO → Type: `Linux`، Version: `Debian (64-bit)`.
   تیک *Skip Unattended Installation* را بزن.
3. سخت‌افزار: **RAM حداقل 4096 MB**، **CPU: 2 یا بیشتر**، تیک **Enable EFI** را بزن.
4. دیسک مجازی: 30 GB (فقط یک فایل روی هاردت است؛ پارتیشن ویندوزت دست نمی‌خورد).
5. بعد از ساخت: **Settings → Display** → Graphics Controller: `VMSVGA`، Video Memory: `128 MB`.
6. **Start**. در منوی بوت `Try without installing` را بزن (۵ ثانیه صبر کنی خودش انتخاب می‌شود).
7. دسکتاپ X-OS با نوار بالا و داک پایین بالا می‌آید و **X-OS Setup** باز می‌شود:
   زبان (فارسی) → صفحه‌کلید (English + Persian، جابه‌جایی Alt+Shift) → اینترنت → ظاهر → مرورگرها.
8. امتحان کن: منوهای نوار بالا، مرکز کنترل (شفافیت داک)، کلیک روی آیکن‌های داک.

**امتحان نصب (فقط داخل ماشین مجازی):** در X-OS Setup دکمه‌ی «نصب X-OS…» → «پاک کردن دیسک»
روی همان دیسک مجازی 30 GB → نام کاربری و رمز → نصب. بعد ماشین را خاموش کن،
در **Settings → Storage** فایل ISO را از درایو CD بردار و دوباره روشن کن تا X-OS نصب‌شده بالا بیاید.

## ۳. امتحان روی کامپیوتر خودت با فلش — بدون نصب

1. یک فلش ۸ گیگ (**همه‌ی محتوایش پاک می‌شود**).
2. **Rufus** را از `rufus.ie` بگیر → فلش را انتخاب کن → ISO → START →
   وقتی پرسید **«Write in DD Image mode»** را انتخاب کن.
3. در ویندوز **Fast Startup** را خاموش کن (Control Panel → Power Options → Choose what the power buttons do).
4. **Secure Boot لازم نیست خاموش شود.** X-OS با زنجیره‌ی امضاشده (shim مایکروسافت + GRUB و کرنل امضاشده‌ی Debian) بوت می‌شود.
   اگر کامپیوترت باز هم اجازه نداد، فقط آن‌وقت Secure Boot را موقتاً خاموش کن.
5. ری‌استارت و کلید منوی بوت: Dell `F12` · HP `F9` · Lenovo `F12` · ASUS `F8`/`Esc` · Acer `F12` · MSI `F11`.
6. فلش (گزینه‌ی `UEFI:`) را انتخاب کن → **Try without installing**.
7. وای‌فای، صدا، تصویر، تاچ‌پد، بلوتوث، نور صفحه و باتری را امتحان کن و نتیجه را برایم بفرست.
   فهرست کامل: `documentation/HARDWARE-TESTING.md`.

در این حالت **هیچ چیزی روی هارد ویندوز نوشته نمی‌شود.** با خاموش کردن و برداشتن فلش، ویندوز مثل قبل بالا می‌آید.

## اگر مشکلی دیدی

- صفحه سیاه ماند → در منوی بوت `Safe graphics (nomodeset)` را امتحان کن.
- کامپیوتر ضعیف (۲–۴ گیگ رم) → `Try without installing (LITE profile)`.
- یک عکس از صفحه و مدل کامپیوترت را بفرست.

**نصب کامل کنار ویندوز (Dual Boot) را فعلاً انجام نده** — شرایطش در
`documentation/INSTALL-FROM-WINDOWS.fa.md` و `documentation/RELEASE-GATES.md` نوشته شده.

</div>
