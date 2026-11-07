using System;
using ZOSAPI;

namespace ZemaxMcp.Fixtures
{
    public sealed class ScalarCallback : APINetCallback
    {
        public static double Transform(double input) { return 2.0 * input; }

        public override int Execute()
        {
            double input;
            if (Settings == null || !Settings.GetDoubleValue("input", out input)) return 10;
            if (Double.IsNaN(input) || Double.IsInfinity(input)) return 11;
            Settings.SetDoubleValue("output", Transform(input));
            Settings.SetStringValue("fixture", "ScalarCallback045");
            return 0;
        }
    }
}
