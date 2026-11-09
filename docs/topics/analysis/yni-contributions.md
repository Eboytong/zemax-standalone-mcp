# YNI Contributions

`run_analysis` accepts `{"kind":"yni_contributions"}`. The request has no additional selectors because the installed OpticStudio 24.2 analysis exposes only `AS_Default`; the native report supplies its wavelength and unit context.

Results include native text, a paginated `rows` table (`surface`, `value`, `unit`) and a `series` curve with surface number on X and YNI contribution on Y. `wavelength_um` and `position_unit` come from the report/system context. The native report values remain the source of record.



## Explicit wavelength

Supply `{"kind":"yni_contributions","wavelength":2}` to query the formal YNIP operand at each optical surface. Wavelength is a positive system wavelength index. Results identify `native_YNIP_operand`, actual Surf/Wave arguments, configuration, wavelength in micrometers and lens units. Rows and series support normal task paging. This path owns no separate native analysis or SystemTool. Omitting wavelength retains the native report and text artifact.
