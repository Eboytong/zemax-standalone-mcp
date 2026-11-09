# YNI Contributions

`run_analysis` accepts `{"kind":"yni_contributions"}`. The request has no additional selectors because the installed OpticStudio 24.2 analysis exposes only `AS_Default`; the native report supplies its wavelength and unit context.

Results include native text, a paginated `rows` table (`surface`, `value`, `unit`) and a `series` curve with surface number on X and YNI contribution on Y. `wavelength_um` and `position_unit` come from the report/system context. The native report values remain the source of record.

Cooke 40 degree field native acceptance returned six surface rows at 0.55000 µm in millimeters. Every parsed value matched the native text exactly at the report's five decimal places. Evidence: [YNI acceptance](../../../development/evidence/CV-01/yni-contributions-acceptance20261108.md).

2026-11-08结果处理加固：非有限贡献、损坏数值行、非递增面号以及非有限/非正波长返回具体错误；普通46项与原生1项通过，补分页、模型保持及关闭断言。显式波长选择待本机YNIP正式替代路径验证，完整条目保持implemented。详见`development/evidence/CV-01/yni-recovery-audit-20261108.md`。

## Explicit wavelength

Supply `{"kind":"yni_contributions","wavelength":2}` to query the formal YNIP operand at each optical surface. Wavelength is a positive system wavelength index. Results identify `native_YNIP_operand`, actual Surf/Wave arguments, configuration, wavelength in micrometers and lens units. Rows and series support normal task paging. This path owns no separate native analysis or SystemTool. Omitting wavelength retains the native report and text artifact.

Cooke six-surface comparison and independent signed spherical `Y*N*I=Y²/R` references passed on 2026-11-08. Full item accepted; see `development/evidence/CV-01/yni-explicit-wavelength-acceptance20261108.md`. Earlier selector-pending notes are historical.
