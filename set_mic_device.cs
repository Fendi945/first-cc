using System;
using System.Runtime.InteropServices;
using System.Text;

class SetMicDevice
{
    // Core Audio API
    enum EDataFlow { eRender, eCapture, eAll }
    enum ERole { eConsole, eMultimedia, eCommunications }

    [ComImport, Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMMDevice
    {
        int Activate(ref Guid iid, uint dwClsCtx, IntPtr pActivationParams, out object ppInterface);
        int OpenPropertyStore(uint stgmAccess, out IntPtr ppProperties);
        int GetId([MarshalAs(UnmanagedType.LPWStr)] out string ppstrId);
        int GetState(out uint pdwState);
    }

    [ComImport, Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMMDeviceEnumerator
    {
        int EnumAudioEndpoints(EDataFlow dataFlow, uint dwStateMask, out IMMDeviceCollection ppDevices);
        int GetDefaultAudioEndpoint(EDataFlow dataFlow, ERole role, out IMMDevice ppEndpoint);
        int GetDevice([MarshalAs(UnmanagedType.LPWStr)] string pwstrId, out IMMDevice ppDevice);
        int RegisterEndpointNotificationCallback(object pClient);
    }

    [ComImport, Guid("0BD7A1BE-7A1A-44DB-8397-CC5392387B5E"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMMDeviceCollection
    {
        int GetCount(out uint pcDevices);
        int Item(uint nDevice, out IMMDevice ppDevice);
    }

    [ComImport, Guid("870AF99C-171D-4F9E-AF0D-E63DF40C2BC9")]
    class CPolicyConfigClient { }

    [ComImport, Guid("F8679F50-850A-41CF-9C72-430F290290C8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IPolicyConfig
    {
        int GetMixFormat(string pszDeviceName, out IntPtr ppFormat);
        int GetDeviceFormat(string pszDeviceName, bool bDefault, out IntPtr ppFormat);
        int ResetDeviceFormat(string pszDeviceName);
        int SetDeviceFormat(string pszDeviceName, IntPtr pFormat, IntPtr ppFormat);
        int GetProcessingPeriod(string pszDeviceName, bool bDefault, out long pmftDefaultPeriod);
        int SetProcessingPeriod(string pszDeviceName, long pmftDefaultPeriod);
        int GetShareMode(string pszDeviceName, out IntPtr pmode);
        int SetShareMode(string pszDeviceName, IntPtr mode);
        int GetPropertyValue(string pszDeviceName, bool bOpenStore, ref Guid guidKey, out IntPtr pv);
        int SetPropertyValue(string pszDeviceName, bool bOpenStore, ref Guid guidKey, IntPtr pv);
        int SetDefaultEndpoint(string pszDeviceName, ERole role);
        int SetEndpointVisibility(string pszDeviceName, bool bVisible);
    }

    [ComImport, Guid("568B9108-44BF-40B4-9166-F8D0395B91BB"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IPolicyConfigVista
    {
        int GetMixFormat(string pszDeviceName, out IntPtr ppFormat);
        int GetDeviceFormat(string pszDeviceName, bool bDefault, out IntPtr ppFormat);
        int ResetDeviceFormat(string pszDeviceName);
        int SetDeviceFormat(string pszDeviceName, IntPtr pFormat, IntPtr ppFormat);
        int GetProcessingPeriod(string pszDeviceName, bool bDefault, out long pmftDefaultPeriod);
        int SetProcessingPeriod(string pszDeviceName, long pmftDefaultPeriod);
        int GetShareMode(string pszDeviceName, out IntPtr pmode);
        int SetShareMode(string pszDeviceName, IntPtr mode);
        int GetPropertyValue(string pszDeviceName, bool bOpenStore, ref Guid guidKey, out IntPtr pv);
        int SetPropertyValue(string pszDeviceName, bool bOpenStore, ref Guid guidKey, IntPtr pv);
        int SetDefaultEndpoint(string pszDeviceName, ERole role);
        int SetEndpointVisibility(string pszDeviceName, bool bVisible);
    }

    // IMMDevice activation for IAudioEndpointVolume
    static Guid IID_IAudioEndpointVolume = new Guid("5CDF2C82-841E-4546-9722-0CF74078229A");
    static Guid CLSID_MMDeviceEnumerator = new Guid("BCDE0395-E52F-467C-8E3D-C4579291692E");
    static Guid IID_IMMDeviceEnumerator = new Guid("A95664D2-9614-4F35-A746-DE8DB63617E6");

    [ComImport, Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IAudioEndpointVolume
    {
        int RegisterControlChangeNotify(object pNotify);
        int UnregisterControlChangeNotify(object pNotify);
        int GetChannelCount(out uint pnChannelCount);
        int SetMasterVolumeLevel(float fLevelDB, ref Guid pguidEventContext);
        int SetMasterVolumeLevelScalar(float fLevel, ref Guid pguidEventContext);
        int GetMasterVolumeLevel(out float pfLevelDB);
        int GetMasterVolumeLevelScalar(out float pfLevel);
        int SetChannelVolumeLevel(uint nChannel, float fLevelDB, ref Guid pguidEventContext);
        int SetChannelVolumeLevelScalar(uint nChannel, float fLevel, ref Guid pguidEventContext);
        int GetChannelVolumeLevel(uint nChannel, out float pfLevelDB);
        int GetChannelVolumeLevelScalar(uint nChannel, out float pfLevel);
        int SetMute([MarshalAs(UnmanagedType.Bool)] bool bMute, ref Guid pguidEventContext);
        int GetMute(out bool pbMute);
        int GetVolumeStepInfo(out uint pnStep, out uint pnStepCount);
        int VolumeStepUp(ref Guid pguidEventContext);
        int VolumeStepDown(ref Guid pguidEventContext);
        int QueryHardwareSupport(out uint pdwHardwareSupportMask);
        int GetVolumeRange(out float pflVolumeMindB, out float pflVolumeMaxdB, out float pflVolumeIncrementdB);
    }

    static Guid GUID_NULL = new Guid("00000000-0000-0000-0000-000000000000");

    static void Main()
    {
        Console.WriteLine("=== ICON UPT4D HW 1/2 录音设备设置 ===");

        try
        {
            // 1. Create device enumerator
            IMMDeviceEnumerator enumerator = (IMMDeviceEnumerator)Activator.CreateInstance(
                Type.GetTypeFromCLSID(CLSID_MMDeviceEnumerator));

            // 2. Enumerate all capture devices
            IMMDeviceCollection devices;
            enumerator.EnumAudioEndpoints(EDataFlow.eCapture, 0x1 | 0x2 | 0x4, out devices);

            uint count;
            devices.GetCount(out count);
            Console.WriteLine($"找到 {count} 个录音设备");

            string hwDeviceId = null;
            string hwFriendlyName = null;

            for (uint i = 0; i < count; i++)
            {
                IMMDevice device;
                devices.Item(i, out device);

                string devId;
                device.GetId(out devId);

                // Get the friendly name from device properties
                uint state;
                device.GetState(out state);

                // Get the property store
                IntPtr propStore;
                device.OpenPropertyStore(0x80000000 /* STGM_READ */, out propStore);

                // Read friendly name property: PKEY_Device_FriendlyName = {a45c254e-df1c-4efd-8020-67d146a850e0}, 14
                var propKey = new PROPERTYKEY(
                    new Guid("a45c254e-df1c-4efd-8020-67d146a850e0"), 14);
                string friendlyName = GetPropStoreValue(propStore, propKey);

                if (!string.IsNullOrEmpty(friendlyName))
                    Console.WriteLine($"  [{i}] {friendlyName} (state={state})");

                // Look for HW 1/2
                if (friendlyName != null && friendlyName.Contains("HW 1/2"))
                {
                    hwDeviceId = devId;
                    hwFriendlyName = friendlyName;
                    Console.WriteLine($"  ^^^ 找到 HW 1/2!");
                }

                Marshal.ReleaseComObject(device);
            }

            if (hwDeviceId != null)
            {
                Console.WriteLine($"\n目标设备: {hwFriendlyName}");
                Console.WriteLine($"设备ID: {hwDeviceId}");

                // 3. Get the device object
                IMMDevice hwDevice;
                enumerator.GetDevice(hwDeviceId, out hwDevice);

                // 4. Activate the endpoint volume interface
                object endpointVolObj;
                int hr = hwDevice.Activate(IID_IAudioEndpointVolume, 0, IntPtr.Zero, out endpointVolObj);

                if (hr == 0 && endpointVolObj != null)
                {
                    IAudioEndpointVolume endpointVol = (IAudioEndpointVolume)endpointVolObj;

                    // Check mute state
                    bool isMuted;
                    endpointVol.GetMute(out isMuted);
                    Console.WriteLine($"当前静音状态: {isMuted}");

                    if (isMuted)
                    {
                        // Unmute
                        Console.WriteLine("正在取消静音...");
                        endpointVol.SetMute(false, ref GUID_NULL);
                        Console.WriteLine("已取消静音 ✓");
                    }

                    // Get current volume
                    float currentLevel;
                    endpointVol.GetMasterVolumeLevelScalar(out currentLevel);
                    Console.WriteLine($"当前音量: {currentLevel * 100:F0}%");

                    // Set volume to 100% if low
                    if (currentLevel < 0.9f)
                    {
                        Console.WriteLine("正在将音量设为 100%...");
                        endpointVol.SetMasterVolumeLevelScalar(1.0f, ref GUID_NULL);
                        Console.WriteLine("音量已设为 100% ✓");
                    }

                    Marshal.ReleaseComObject(endpointVol);
                }
                else
                {
                    Console.WriteLine($"无法激活音量控制 (hr=0x{hr:X8})");
                }

                // 5. Set as default device via PolicyConfig
                try
                {
                    Console.WriteLine("\n正在设为默认通信设备...");

                    // Try IPolicyConfig first (Windows 7+)
                    try
                    {
                        var policyConfig = new CPolicyConfigClient();
                        var policy = (IPolicyConfig)policyConfig;
                        policy.SetDefaultEndpoint(hwDeviceId, ERole.eCommunications);
                        policy.SetDefaultEndpoint(hwDeviceId, ERole.eConsole);
                        Console.WriteLine("已设为默认设备 ✓ (IPolicyConfig)");
                        Marshal.ReleaseComObject(policy);
                    }
                    catch
                    {
                        Console.WriteLine("IPolicyConfig 失败，尝试 IPolicyConfigVista...");
                        try
                        {
                            var policyConfig2 = new CPolicyConfigClient();
                            var policy2 = (IPolicyConfigVista)policyConfig2;
                            policy2.SetDefaultEndpoint(hwDeviceId, ERole.eCommunications);
                            policy2.SetDefaultEndpoint(hwDeviceId, ERole.eConsole);
                            Console.WriteLine("已设为默认设备 ✓ (IPolicyConfigVista)");
                            Marshal.ReleaseComObject(policy2);
                        }
                        catch (Exception ex2)
                        {
                            Console.WriteLine($"IPolicyConfigVista 也失败: {ex2.Message}");
                        }
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"设置默认设备失败: {ex.Message}");
                }

                Marshal.ReleaseComObject(hwDevice);
            }
            else
            {
                Console.WriteLine("\n❌ 没有找到 UPT4D HW 1/2 设备！");
                Console.WriteLine("请确认声卡已正确连接并安装了驱动。");
            }

            Marshal.ReleaseComObject(enumerator);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"错误: {ex.Message}");
            Console.WriteLine(ex.StackTrace);
        }

        Console.WriteLine("\n完成。按任意键退出...");
        Console.ReadKey();
    }

    struct PROPERTYKEY
    {
        public Guid fmtid;
        public int pid;
        public PROPERTYKEY(Guid fmtid, int pid)
        {
            this.fmtid = fmtid;
            this.pid = pid;
        }
    }

    // IPropertyStore native methods
    [ComImport, Guid("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IPropertyStore
    {
        void GetCount(out uint cProps);
        void GetAt(uint iProp, out PROPERTYKEY pkey);
        void GetValue(ref PROPERTYKEY key, out PROPVARIANT pv);
        void SetValue(ref PROPERTYKEY key, ref PROPVARIANT pv);
        void Commit();
    }

    [StructLayout(LayoutKind.Sequential)]
    struct PROPVARIANT
    {
        public ushort vt;
        public ushort wReserved1;
        public ushort wReserved2;
        public ushort wReserved3;
        public IntPtr data1;
        public IntPtr data2;
    }

    static string GetPropStoreValue(IntPtr propStorePtr, PROPERTYKEY key)
    {
        try
        {
            IPropertyStore store = (IPropertyStore)Marshal.GetObjectForIUnknown(propStorePtr);
            PROPVARIANT pv;
            store.GetValue(ref key, out pv);

            if (pv.vt == 0x1F) // VT_LPWSTR
            {
                return Marshal.PtrToStringUni(pv.data1);
            }
            else if (pv.vt == 0x1E) // VT_LPSTR
            {
                return Marshal.PtrToStringAnsi(pv.data1);
            }
        }
        catch { }
        return null;
    }
}
