using System;
using System.IO;
using System.Reflection;
using ZOSAPI;

namespace ZemaxMcp.Fixtures
{
    internal static class NativeSagOperand
    {
        private static void Trace(string message)
        {
            string name = Path.GetFileNameWithoutExtension(Assembly.GetExecutingAssembly().Location);
            string path = Path.Combine(Path.GetTempPath(), name + ".trace");
            File.AppendAllText(path, DateTime.UtcNow.ToString("O") + " " + message + Environment.NewLine);
        }

        private static int Main()
        {
            try
            {
                Trace("started");
            }
            catch { }
            string installDir = Path.GetDirectoryName(typeof(IZOSAPI_Application).Assembly.Location);
            if (!ZOSAPI_NetHelper.ZOSAPI_Initializer.Initialize(installDir))
                return 90;

            IZOSAPI_Application app = null;
            try
            {
                var connection = new ZOSAPI_Connection();
                app = connection.ConnectToApplication();
                if (app == null || app.Mode != ZOSAPI_Mode.Operand)
                    return 91;

                int count = app.OperandResults.Length;
                var values = new double[count];
                int surface = (int)app.OperandArgument1;
                double x = app.OperandArgument3;
                double y = app.OperandArgument4;
                var system = app.PrimarySystem;
                Trace("connected mode=" + app.Mode + " surface=" + surface + " x=" + x + " y=" + y + " result_count=" + count);
                if (surface < 0 || surface >= system.LDE.NumberOfSurfaces)
                {
                    values[0] = 1e9;
                    values[1] = 1e9;
                }
                else
                {
                    double sag;
                    double slope;
                    system.LDE.GetSag(surface, x, y, out sag, out slope);
                    values[0] = sag;
                    values[1] = slope;
                    Trace("sag=" + sag.ToString("R") + " slope=" + slope.ToString("R"));
                }

                app.OperandResults.WriteData(values.Length, values);
                Trace("write_succeeded first=" + values[0].ToString("R"));
                return 0;
            }
            catch (Exception ex)
            {
                try { Trace("exception=" + ex); }
                catch { }
                try
                {
                    string errorPath = Path.Combine(Path.GetTempPath(),
                        Path.GetFileNameWithoutExtension(Assembly.GetExecutingAssembly().Location) + ".error.txt");
                    File.WriteAllText(errorPath, ex.ToString());
                }
                catch { }
                return 92;
            }
        }
    }
}
