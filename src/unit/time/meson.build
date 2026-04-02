module_sources = files('orbit_time.cpp')

module_inc = include_directories('.')

sap_unit_time_lib = library('sap_unit_time',
    module_sources,
    include_directories: module_inc,
    install: false,
)

unit_time_dep = declare_dependency(
    link_with: sap_unit_time_lib,
    include_directories: module_inc,
)

sap_module_deps += {'unit_time_dep': unit_time_dep}
