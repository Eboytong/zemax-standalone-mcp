"""Cooke requests and explicit owners of analyses requiring another fixture."""

# These tests exercise their own model/resource and failure contracts. Listing
# them here routes coverage; their presence is not evidence of a native pass.
SPECIALIZED = {
    'detector_viewer':('test_detector_viewer_live.py','NSC current accumulation or selected ZRD'),
    'extended_diffraction_image':('test_scene_images_live.py','scene input and explicit source/display widths'),
    'partially_coherent_image':('test_scene_images_live.py','scene CFG, field/wavelength selection and native grid'),
    'biocular_field_of_view':('test_biocular_fov_live.py','native STOP-launched multi-configuration pass boundary'),
    'biocular_dipvergence_convergence':('test_biocular_live.py','controlled two-configuration chief-ray matching'),
    'yybar_diagram':('test_ray_diagrams_live.py','native first-order ray diagram'),
    'incident_angle_vs_image_height':('test_ray_diagrams_live.py','native real-ray signed incidence diagram'),
    'sag_table':('test_sag_table_live.py','native manufacturing sag and BFS operand reference'),
    'paraxial_gaussian_beam': ('test_gaussian_beams_live.py', 'controlled native Gaussian operand propagation'),
    'skew_gaussian_beam': ('test_gaussian_beams_live.py', 'controlled chief-ray Gaussian propagation'),
    'file_comparator': ('test_comparator_live.py', 'two independently saved lens files'),
    'polarization_pupil_map': ('test_polarization_live.py', 'controlled polarized interface'),
    'image_simulation': ('test_image_simulation_reference_live.py', 'registered source image'),
    'geometric_image': ('test_geometric_image_reference_live.py', 'registered source image'),
    'geometric_bitmap_image': ('test_imaging_live.py', 'native AS_Default interface limitation'),
    'extended_source_encircled_energy': ('test_imaging_live.py', 'registered extended-source image'),
    'grin_profile': ('test_grin_profile_live.py', 'gradient-index surface'),
    'nsc_surface_sag': ('test_nsc_sag_reference_live.py', 'NSC object and face selection'),
    'nsc_geometric_mtf': ('test_nsc_mtf_live.py', 'traced NSC detector'),
    'path_analysis': ('test_nsc_path_live.py', 'traced ZRD database'),
    'critical_ray_trace': ('test_nsc_analyses_live.py', 'critical-ray input file'),
    'nsc_single_ray_trace': ('test_nsc_analyses_live.py', 'NSC model'),
    'internal_transmission_vs_wavelength': ('test_materials_live.py', 'material catalog and glass identities'),
    'quick_yield': ('test_tolerance_special_analyses_live.py', 'controlled tolerance operands'),
    'tolerance_yield': ('test_tolerance_special_analyses_live.py', 'tolerance results'),
    'tolerance_histogram': ('test_tolerance_special_analyses_live.py', 'tolerance results'),
    'full_field_spot': ('test_full_field_spot_live.py', 'dedicated result-outlet contract'),
    'matrix_spot': ('test_configuration_matrix_spot_live.py', 'native matrix result-outlet limitation'),
    'configuration_matrix_spot': ('test_configuration_matrix_spot_live.py', 'multi-configuration model and native result-outlet limitation'),
    'ima_bim_viewer': ('test_ima_viewer_live.py', 'owned IMA/BIM source image and layer selection'),
    'ray_database_viewer': ('test_ray_database_viewer_live.py', 'owned ZRD database and segment selection'),
    'power_field_map': ('test_power_maps_live.py', 'sequential surface and physical field extent'),
    'power_pupil_map': ('test_power_maps_live.py', 'sequential surface and normalized pupil extent'),
    'surface_phase': ('test_phase_slope_reference_live.py', 'phase surface'),
    'surface_phase_cross': ('test_phase_slope_reference_live.py', 'phase surface'),
    'surface_phase_slope': ('test_phase_slope_reference_live.py', 'phase surface'),
    'surface_phase_slope_cross': ('test_phase_slope_reference_live.py', 'phase surface'),
    # Kind-only requests by contract: the native settings object exposes no documented
    # section or surface selector, so adding a Cooke default would be a fabricated field.
    'prescription_data': ('test_native_text_reports_live.py', 'default report scope only; no documented section selector'),
    'surface_data': ('test_native_text_reports_live.py', 'default report scope only; no documented surface selector'),
}
for kind in ('star_align_check','star_sys_viewer','star_2d_def_plot',
             'star_perf_change','star_index_vs_temp','star_inspect_fea'):
    SPECIALIZED[kind] = ('test_star_analysis_live.py', 'enabled STAR module and controlled FEA input')
for metric in ['reflection','transmission','absorption','diattenuation','phase','retardance']:
    for axis in ['angle','wavelength']:
        SPECIALIZED[f'{metric}_vs_{axis}'] = ('test_coatings_live.py', 'selected coating surface and polarization reference')
SPECIALIZED['coating_listing'] = ('test_coatings_live.py', 'selected coating surface')
for kind in ['diff_efficiency_2d','diff_efficiency_angular','diff_efficiency_chromatic']:
    SPECIALIZED[kind] = ('test_diff_efficiency_offaxis_live.py', 'volume hologram or controlled DLL surface')

# Confirmed by outlets265: all public result arrays empty, GetTextFile=false.
# Reproducing a limitation is kept separate from successful analysis coverage.
EXPECTED_LIMITATIONS = {}
# seidel_diagram auto now builds a documented bar chart from native coefficients;
# explicit method=native retains the outlet limitation in test_seidel_slopes_live.


def cooke_request(kind):
    q = {'kind': kind}
    if kind == 'universal_plot_1d':
        q.update(surface=1, start=2, stop=4, samples=3, first_surface=1, last_surface=1)
    elif kind == 'universal_plot_2d':
        q.update(x=dict(surface=1, start=2, stop=4, samples=3),
                 y=dict(surface=2, start=3, stop=5, samples=3), first_surface=1, last_surface=2)
    elif kind == 'grid_distortion':
        q['field_width'] = 10
    elif kind.endswith('_mtf_map'):
        q.update(x_field_width=4, y_field_width=4, x_pixels=3, y_pixels=3)
    elif kind == 'zernike_fringe':
        q['maximum_terms'] = 37
    elif kind.startswith('surface_') or kind == 'footprint':
        q['surface'] = 1
    return q
