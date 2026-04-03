project(
    'statellite_autonomy_plugin',
    ['c', 'cpp'],
    version: '0.1.0',
    license: 'MIT',
    meson_version: '>= 0.64.0',
    default_options: [
        'warning_level=2',
        'c_std=c11',
        'cpp_std=c++17',
    ],
)

target_system = meson.is_cross_build() ? host_machine.system() : build_machine.system()
target_arch = meson.is_cross_build() ? host_machine.cpu_family() : build_machine.cpu_family()

sap_dependencies = {}
enable_tests = get_option('enable_tests')
gtest_main_dep = dependency('', required: false)

if enable_tests
    gtest_sub = subproject('gtest', required: true,
        default_options: ['cpp_std=c++17'])
    gtest_main_dep = gtest_sub.get_variable('gtest_main_dep')
    sap_dependencies += {'gtest_main_dep': gtest_main_dep}
endif

sap_module_deps = {}

subdir('product')

summary({
    'Project': meson.project_name(),
    'Version': meson.project_version(),
    'Target': '@0@-@1@'.format(target_system, target_arch),
    'Tests': enable_tests,
    'GTest': enable_tests,
}, section: 'statellite_autonomy_plugin')
