# Google Test meson build (overlay for wrap-git)
project('gtest', 'cpp',
    version: '1.14.0',
    license: 'BSD-3-Clause',
    default_options: [
        'cpp_std=c++17',
        'default_library=static',
        'warning_level=0',
    ],
)

gtest_inc = include_directories('googletest/include', 'googletest')
gtest_src = files(
    'googletest/src/gtest-all.cc',
)
gtest_lib = library('gtest',
    gtest_src,
    include_directories: gtest_inc,
    install: false,
)
gtest_dep = declare_dependency(
    link_with: gtest_lib,
    include_directories: gtest_inc,
)

gtest_main_src = files('googletest/src/gtest_main.cc')
gtest_main_lib = library('gtest_main',
    gtest_main_src,
    link_with: gtest_lib,
    include_directories: gtest_inc,
    install: false,
)
gtest_main_dep = declare_dependency(
    link_with: gtest_main_lib,
    include_directories: gtest_inc,
    dependencies: gtest_dep,
)

meson.override_dependency('gtest', gtest_dep)
