Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public class MicFix
{
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

    static Guid IID_IAudioEndpointVolume = new Guid("5CDF2C82-841E-4546-9722-0CF74078229A");
    static Guid CLSID_MMDeviceEnumerator = new Guid("BCDE0395-E52F-467C-8E3D-C4579291692E");
    static Guid GUID_NULL = new Guid();

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

    [StructLayout(LayoutKind.Sequential)]
    struct PROPERTYKEY
    {
        public Guid fmtid;
        public int pid;
    }

    const uint STGM_READ = 0x80000000;

    public static void Run()
    {
        Console.WriteLine("=== ICON UPT4D HW 1/2 Audio Setup ===");
        try
        {
            Type enumType = Type.GetTypeFromCLSID(CLSID_MMDeviceEnumerator);
            IMMDeviceEnumerator enumerator = (IMMDeviceEnumerator)Activator.CreateInstance(enumType);

            IMMDeviceCollection devices;
            enumerator.EnumAudioEndpoints(EDataFlow.eCapture, 0x1 | 0x2 | 0x4, out devices);
            uint count;
            devices.GetCount(out count);
            Console.WriteLine("Found " + count + " recording devices");

            string hwDeviceId = null;
            string hwFriendlyName = null;

            for (uint i = 0; i < count; i++)
            {
                IMMDevice device;
                devices.Item(i, out device);
                string devId;
                device.GetId(out devId);

                string friendlyName = GetFriendlyName(device);
                string displayName = friendlyName ?? "Unknown";
                Console.WriteLine("  [" + i + "] " + displayName);

                if (friendlyName != null && friendlyName.Contains("HW 1/2"))
                {
                    hwDeviceId = devId;
                    hwFriendlyName = displayName;
                }
                Marshal.ReleaseComObject(device);
            }

            if (hwDeviceId != null)
            {
                Console.WriteLine("\nTarget: " + hwFriendlyName);

                IMMDevice hwDevice;
                enumerator.GetDevice(hwDeviceId, out hwDevice);

                object epVolObj;
                int hr = hwDevice.Activate(IID_IAudioEndpointVolume, 0, IntPtr.Zero, out epVolObj);
                if (hr == 0 && epVolObj != null)
                {
                    IAudioEndpointVolume epVol = (IAudioEndpointVolume)epVolObj;
                    bool muted;
                    epVol.GetMute(out muted);
                    Console.WriteLine("Muted: " + (muted ? "YES -> unmuting..." : "NO"));
                    if (muted) { epVol.SetMute(false, ref GUID_NULL); Console.WriteLine("  Unmuted OK"); }

                    float vol;
                    epVol.GetMasterVolumeLevelScalar(out vol);
                    Console.WriteLine("Volume: " + (int)(vol * 100) + "%");
                    if (vol < 0.95) { epVol.SetMasterVolumeLevelScalar(1.0f, ref GUID_NULL); Console.WriteLine("  Set to 100%"); }

                    Marshal.ReleaseComObject(epVol);
                }
                else
                {
                    Console.WriteLine("Cannot activate volume control (hr=0x" + hr.ToString("X8") + ")");
                }

                try
                {
                    Console.Write("Setting as default recording device... ");
                    Type policyType = Type.GetTypeFromCLSID(new Guid("870AF99C-171D-4F9E-AF0D-E63DF40C2BC9"));
                    object policyObj = Activator.CreateInstance(policyType);

                    try
                    {
                        policyObj.GetType().InvokeMember("SetDefaultEndpoint",
                            System.Reflection.BindingFlags.InvokeMethod, null, policyObj,
                            new object[] { hwDeviceId, 2 }); // eCommunications
                        System.Threading.Thread.Sleep(200);
                        policyObj.GetType().InvokeMember("SetDefaultEndpoint",
                            System.Reflection.BindingFlags.InvokeMethod, null, policyObj,
                            new object[] { hwDeviceId, 0 }); // eConsole
                        Console.WriteLine("OK");
                    }
                    catch (Exception ex2)
                    {
                        Console.WriteLine("FAILED: " + ex2.Message);
                    }
                    Marshal.ReleaseComObject(policyObj);
                }
                catch (Exception ex)
                {
                    Console.WriteLine("Policy config error: " + ex.Message);
                }

                Marshal.ReleaseComObject(hwDevice);
                Console.WriteLine("\nDone! Test iFlytek voice input now.");
            }
            else
            {
                Console.WriteLine("\nERROR: UPT4D HW 1/2 not found!");
            }

            Marshal.ReleaseComObject(enumerator);
        }
        catch (Exception ex)
        {
            Console.WriteLine("Error: " + ex.Message);
            Console.WriteLine(ex.StackTrace);
        }
    }

    static string GetFriendlyName(IMMDevice device)
    {
        try
        {
            IntPtr propStore;
            device.OpenPropertyStore(STGM_READ, out propStore);
            object propStoreObj = Marshal.GetObjectForIUnknown(propStore);

            PROPERTYKEY key = new PROPERTYKEY();
            key.fmtid = new Guid("a45c254e-df1c-4efd-8020-67d146a850e0");
            key.pid = 14;

            object[] args = new object[] { key };
            object result = propStoreObj.GetType().InvokeMember("GetValue",
                System.Reflection.BindingFlags.InvokeMethod, null, propStoreObj, args);

            if (result != null)
            {
                string val = result.GetType().InvokeMember("GetValue",
                    System.Reflection.BindingFlags.InvokeMethod, null, result, null) as string;
                return val;
            }
        }
        catch { }
        return null;
    }
}
'@

[MicFix]::Run()
