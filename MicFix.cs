using System;
using System.Runtime.InteropServices;
using System.Text;

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
    struct PROPERTYKEY
    {
        public Guid fmtid;
        public int pid;
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

        public string GetString()
        {
            if (vt == 31) return Marshal.PtrToStringUni(data1);
            if (vt == 30) return Marshal.PtrToStringAnsi(data1);
            return null;
        }
    }

    const uint STGM_READ = 0x80000000;

    static string GetDeviceFriendlyName(IMMDevice device)
    {
        try
        {
            IntPtr propStorePtr;
            device.OpenPropertyStore(STGM_READ, out propStorePtr);
            if (propStorePtr == IntPtr.Zero) return null;

            IPropertyStore store = (IPropertyStore)Marshal.GetObjectForIUnknown(propStorePtr);

            PROPERTYKEY key = new PROPERTYKEY();
            key.fmtid = new Guid("a45c254e-df1c-4efd-8020-67d146a850e0");
            key.pid = 14; // PKEY_Device_FriendlyName

            PROPVARIANT pv;
            store.GetValue(ref key, out pv);
            string result = pv.GetString();

            Marshal.ReleaseComObject(store);
            return result;
        }
        catch
        {
            return null;
        }
    }

    public static void Main(string[] args)
    {
        Console.WriteLine("=== ICON UPT4D HW 1/2 Auto Setup ===\n");

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

                string friendlyName = GetDeviceFriendlyName(device);
                string displayName = friendlyName ?? "(unnamed)";
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
                Console.WriteLine("\n>> Target: " + hwFriendlyName);
                Console.WriteLine(">> Device ID: " + hwDeviceId.Substring(0, Math.Min(50, hwDeviceId.Length)) + "...");

                // Get the device and unmute
                IMMDevice hwDevice;
                enumerator.GetDevice(hwDeviceId, out hwDevice);

                object epVolObj;
                int hr = hwDevice.Activate(IID_IAudioEndpointVolume, 0, IntPtr.Zero, out epVolObj);
                if (hr == 0 && epVolObj != null)
                {
                    IAudioEndpointVolume epVol = (IAudioEndpointVolume)epVolObj;

                    bool muted;
                    epVol.GetMute(out muted);
                    if (muted)
                    {
                        Console.Write("Unmuting... ");
                        epVol.SetMute(false, ref GUID_NULL);
                        Console.WriteLine("OK");
                    }

                    float vol;
                    epVol.GetMasterVolumeLevelScalar(out vol);
                    Console.WriteLine("Volume: " + (int)(vol * 100) + "%");
                    if (vol < 0.95)
                    {
                        epVol.SetMasterVolumeLevelScalar(1.0f, ref GUID_NULL);
                        Console.WriteLine("  -> Set to 100%");
                    }

                    Marshal.ReleaseComObject(epVol);
                }

                // Set as default device via IPolicyConfig
                try
                {
                    Console.Write("Setting as default device... ");
                    Guid CLSID_PolicyConfig = new Guid("870AF99C-171D-4F9E-AF0D-E63DF40C2BC9");
                    Type policyType = Type.GetTypeFromCLSID(CLSID_PolicyConfig);
                    object policyObj = Activator.CreateInstance(policyType);

                    bool setOk = false;
                    try
                    {
                        policyObj.GetType().InvokeMember("SetDefaultEndpoint",
                            System.Reflection.BindingFlags.InvokeMethod, null, policyObj,
                            new object[] { hwDeviceId, 0 }); // eConsole
                        System.Threading.Thread.Sleep(300);
                        policyObj.GetType().InvokeMember("SetDefaultEndpoint",
                            System.Reflection.BindingFlags.InvokeMethod, null, policyObj,
                            new object[] { hwDeviceId, 2 }); // eCommunications
                        setOk = true;
                    }
                    catch
                    {
                        try
                        {
                            policyObj.GetType().InvokeMember("SetDefaultEndpoint",
                                System.Reflection.BindingFlags.InvokeMethod, null, policyObj,
                                new object[] { hwDeviceId, 0 });
                            setOk = true;
                        }
                        catch (Exception ex2)
                        {
                            Console.WriteLine("FAILED (" + ex2.Message + ")");
                        }
                    }

                    if (setOk) Console.WriteLine("OK");
                    Marshal.ReleaseComObject(policyObj);
                }
                catch (Exception ex)
                {
                    Console.WriteLine("PolicyConfig error: " + ex.Message);
                }

                Marshal.ReleaseComObject(hwDevice);
                Console.WriteLine("\n----------------------------------------");
                Console.WriteLine("DONE! Default recording device changed to:");
                Console.WriteLine("  " + hwFriendlyName);
                Console.WriteLine("----------------------------------------");
            }
            else
            {
                Console.WriteLine("\nERROR: UPT4D HW 1/2 not found among " + count + " devices!");
                Console.WriteLine("\nAvailable devices show names above. Make sure the");
                Console.WriteLine("ICON UPorts4 Dyna driver is properly installed.");
            }

            Marshal.ReleaseComObject(devices);
            Marshal.ReleaseComObject(enumerator);
        }
        catch (Exception ex)
        {
            Console.WriteLine("Fatal error: " + ex.ToString());
        }

        Console.WriteLine("\nPress any key to exit...");
        Console.ReadKey();
    }
}
