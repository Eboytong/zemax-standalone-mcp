# Gradium GrinProfile波长归属

日期2026-11-09；D002 / MA-01.GradiumProfile，源码0.1.62工作树，项目内Python3.14，OpticStudio24.2.0 build240529 PremiumEdition。

## 计划与范围

接入已准备的Q3用例，确认正式IAS_GrinProfile.Wavelength选择、实际编号和结果的波长依赖；区分材料族参考顶点参数与曲线波长。此次不重复高阶/capping矩阵。现有GRD及SGRIN资源来源为本机Documents/Zemax/Glasscat，参数定义沿已保存手册244—245页。

## 输入、执行与结果

自建四面系统，面2为Gradium/G14SFN，厚0.4 mm、轴向偏移1 mm、步长0.01 mm、capping=3；两波长0.58756与0.55 µm；Z扫描0—0.4 mm，X=Y=0。请求kind=grin_profile、surface=2、wavelength=1/2、show_index_vs=Z，其余见用例和calls.json。

正式Wavelength回读为1和2，101个X节点完全一致；曲线最大绝对差0.0064148708266285048。两次reference_vertex_index均为1.789481740708463。此控制验收的是设置和波长依赖，未将该差值作为独立色散公式的误差。区分门槛1e-12、预期可分离差值大于1e-3；实际满足。生产series新增wavelength_number及index_definition，保留native_axes；原始曲线数值保持。

命令：COMPLUS_LoadFromRemoteSources=1，PYTHONPATH指向主仓src；项目.venv/Scripts/python.exe -B -X utf8 -m pytest --run-zemax -q -p no:cacheprovider tests/native/test_gradium_profile_wavelength_live.py --junitxml=.local/evidence/development/MA-01/gradium-wavelength-labeled-20261109.xml。1 passed，10.57秒；相关普通test_grin_profile.py及test_gradium_profile.py共50 passed，0.53秒。

原始目录：.local/runs/runs/gradium_q3_wavelength_attribution_9625a30b9e，含attribution.json、calls.json、工作副本及关闭回执。两任务succeeded、close_attempted=true、无cleanup warnings；设置、曲面和评价函数保持；disconnect成功且connected=false。首轮准备模型时误写像面厚度被CELL_NOT_WRITABLE拒绝，已移除该项，保留44b14efc08及失败XML；修正后4ffed29d30及本次均通过。

## 状态与下一步

Gradium保持in_progress。波长选择归属缺口已补，完整范围继续保留10/11阶求值差异、负profile/capping段传播及专题选择。解除条件为对应正式求值/边界依据或可复现的最小修复；原门槛保持。完整功能4/10、剩余92组。
