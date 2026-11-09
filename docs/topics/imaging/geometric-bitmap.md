# 几何位图图像分析

`run_analysis`的`geometric_bitmap_image`使用原生GeometricBitmapImageAnalysis、正式GBM配置键和RGB文本结果。当前适配毫米镜头单位、有焦顺序系统。

```json
{"request":{"kind":"geometric_bitmap_image","input_file":"C:/controlled/source.bmp","surface":7,"field_size":1,"rotation":90,"rays_per_pixel":10,"x_pixels":17,"y_pixels":11,"x_pixel_size":0.05,"y_pixel_size":0.05}}
```

输入为存在的BMP/JPG/PNG绝对路径，或原生ImagesDir下的文件名。surface省略时使用像面；field_size是物方全Y高，采用当前物方视场单位；rotation采用度。rays_per_pixel是每源像素、每颜色通道的光线数。X/Y像素大小使用镜头单位，默认各0.01；像素数量默认各256，上限合计400万。

旧请求从GeometricImage继承的rays_x1000、number_of_pixels、image_size、field、wavelength等字段与本专题已确认设置不对应，现返回INVALID_ARGUMENT。使用上例中的位图专用参数。其余未确认配置采用原生当前默认条件，并在结果设置中记录。

设置经SaveTo、ModifySettings、LoadFrom后，以原生报告核对文件、曲面、角度、源尺寸、光线数及像素组合。结果actual_settings保留请求、配置操作、最终回读和任务自有输出文件。

结果grids按R、G、B返回三个8位显示通道。values[y][x]为X向右、Y向上；坐标为像素中心0.5、1.5等。原生文本y=1为显示顶行，适配器转换到Y向上，并检查其与原生BMP显示像素对应。physical_pixel_sizes保留报告尺寸；physical_origin_verified=false。通道值遵循原生显示归一化，功率单位及独立成像参考仍待验收。

使用get_task_result的grid/x_start/y_start/width/height分页，export_analysis_image导出PNG。原生文本和BMP保留为任务文件。全黑输入返回全零通道。
