time_test = executable('test_time',
    'test_time.cpp',
    dependencies: [gtest_main_dep, sap_module_deps['unit_time_dep']],
    install: false,
)

test('time', time_test)

time_benchmark = executable('time_benchmark',
    'time_benchmark.cpp',
    dependencies: [sap_module_deps['unit_time_dep']],
    install: false,
)
