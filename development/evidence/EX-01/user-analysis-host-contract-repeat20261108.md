# User analysis host contract review, 2026-11-08

- Item: `EX-01.UserAnalysisHost`; OpticStudio 24.2.0 build 240529; installed user-analysis sample under `C:\\Users\\tonge\\Documents\\Zemax\\ZOS-API Sample Code\\C#\\SampleAnalysis1.cs` and executable under `C:\\Users\\tonge\\Documents\\Zemax\\ZOS-API Sample Code\\C#\\..\\..\\ZOS-API\\User Analysis\\SampleAnalysis1.exe`.
- Official sample contract: it calls `ZOSAPI_Connection.ConnectToApplication()`, then accepts only `ZOSAPI_Mode.UserAnalysis` and `UserAnalysisSettings`. In analysis mode it reads `UserAnalysisData.UserSettings`, runs a native FFT MTF analysis, and publishes data through `IUserAnalysisData` plot methods. Settings mode uses a WinForms dialog and writes the selected wavelength back.
- Current host boundary: the MCP-owned application starts in Standalone mode. Current reflection records `ConnectToApplication` but no application API to launch this sample in UserAnalysis/UserAnalysisSettings mode. The sample is therefore not callable as a standalone host operation through the current MCP interface.
- No user-analysis executable was launched in the wrong mode; no UI or model mutation was introduced. Existing files establish the official source and executable are present locally.
- Blocker and release condition: obtain a formal OpticStudio user-analysis launch/registration mechanism, or run the sample under an explicitly controlled UserAnalysis host context. Then verify settings, analysis output, process termination, result ownership and close behavior.
- Completion count: 0.
