from conans import ConanFile, tools
import os

def b2_options(conanfile, lib_name=None):
    result = ""
    if hasattr(conanfile, 'b2_options'):
        result += conanfile.b2_options(lib_name=lib_name)
    for lib_name in source_only_deps(conanfile, lib_name):
        result += ' include=' + lib_name + '/include'
    return result


def is_header_only(conanfile, lib_name=None):
    try:
        if type(conanfile.is_header_only) == bool:
            return conanfile.is_header_only
        elif lib_name:
            return conanfile.is_header_only[lib_name]
        else:
            for lib_name in conanfile.lib_short_names:
                if not is_header_only(conanfile, lib_name):
                    return False
    except Exception:
        pass
    return True

def source_only_deps(conanfile, lib_name):
    try:
        return conanfile.source_only_deps[lib_name]
    except Exception:
        pass
    try:
        return conanfile.source_only_deps
    except Exception:
        pass
    return []

def is_in_cycle_group(conanfile):
    try:
        return conanfile.is_in_cycle_group
    except Exception:
        return False

def is_cycle_group(conanfile):
    try:
        return conanfile.is_cycle_group
    except Exception:
        return False

def source(conanfile):
    # print(">>>>> conanfile.source: " + str(conanfile))
    if not is_in_cycle_group(conanfile):
        boostorg_github = "https://github.com/boostorg"
        archive_name = "boost-" + conanfile.version
        libs_to_get = list(conanfile.lib_short_names)
        for lib_short_name in conanfile.lib_short_names:
            libs_to_get.extend(source_only_deps(conanfile, lib_short_name))
        for lib_short_name in libs_to_get:
            tools.get("{0}/{1}/archive/{2}.tar.gz"
                .format(boostorg_github, lib_short_name, archive_name))
            os.rename(lib_short_name + "-" + archive_name, lib_short_name)
        getattr(conanfile, "source_after", lambda:None)()

def build(conanfile):
    # print(">>>>> conanfile.build: " + str(conanfile))
    for lib_short_name in conanfile.lib_short_names:
        if is_header_only(conanfile, lib_short_name):
            if not is_cycle_group(conanfile):
                lib_dir = os.path.join(lib_short_name, "lib")
                if not os.path.exists(lib_dir):
                    os.makedirs(lib_dir)
                with open(os.path.join(lib_dir, "jamroot.jam"), "w") as f:
                    f.write("""
import project ;
project /conan/{0} ;
project.register-id /boost/{0} : $(__name__) ;""".format(lib_short_name))
        elif not is_in_cycle_group(conanfile):
            conanfile.run(conanfile.deps_user_info['Boost.Generator'].b2_command \
                + " " + b2_options(conanfile, lib_short_name) \
                + " %s-build" % (lib_short_name))
    getattr(conanfile, "build_after", lambda:None)()

def package(conanfile, *subdirs_to_package):
    # print(">>>>> conanfile.package: " + str(conanfile))
    if not subdirs_to_package:
        subdirs_to_package = []
    subdirs_to_package.extend(["lib", "include"])
    for lib_short_name in conanfile.lib_short_names:
        for subdir in subdirs_to_package:
            copydir = os.path.join(lib_short_name, subdir)
            conanfile.copy(pattern="*", dst=copydir, src=copydir)
    getattr(conanfile, "package_after", lambda:None)()

def package_info(conanfile):
    # print(">>>>> conanfile.package_info: " + str(conanfile))
    conanfile.user_info.lib_short_names = ",".join(conanfile.lib_short_names)
    conanfile.cpp_info.includedirs = []
    conanfile.cpp_info.libdirs = []
    conanfile.cpp_info.libs = []
    if is_in_cycle_group(conanfile):
        if not is_header_only(conanfile):
            for lib_dir in conanfile.deps_cpp_info.lib_paths:
                if os.path.basename(os.path.dirname(lib_dir)) == conanfile.lib_short_names[0]:
                    conanfile.cpp_info.libs.extend(tools.collect_libs(conanfile, lib_dir))
    elif is_cycle_group(conanfile):
        for lib_short_name in conanfile.lib_short_names:
            lib_dir = os.path.join(lib_short_name, "lib")
            conanfile.cpp_info.libdirs.append(lib_dir)
            include_dir = os.path.join(lib_short_name, "include")
            conanfile.cpp_info.includedirs.append(include_dir)
    else:
        for lib_short_name in conanfile.lib_short_names:
            lib_dir = os.path.join(lib_short_name, "lib")
            conanfile.cpp_info.libdirs.append(lib_dir)
            conanfile.cpp_info.libs.extend(tools.collect_libs(conanfile, lib_dir))
            include_dir = os.path.join(lib_short_name, "include")
            conanfile.cpp_info.includedirs.append(include_dir)
    conanfile.cpp_info.defines.append("BOOST_ALL_NO_LIB=1")
    getattr(conanfile, "package_info_after", lambda:None)()