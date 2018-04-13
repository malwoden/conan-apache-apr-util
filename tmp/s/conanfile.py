from conans import ConanFile, AutoToolsBuildEnvironment, CMake, tools
import os, glob, shutil, ntpath

class ApacheaprutilConan(ConanFile):
    name = "apache-apr-util"
    version = "1.6.1"
    license = "Apache-2.0"
    url = "https://github.com/malwoden/conan-apache-apr-util"
    settings = "os", "compiler", "build_type", "arch"
    requires = "apache-apr/1.6.3@neewill/testing", "Expat/2.2.5@bincrafters/stable"
    options = {"shared": [True, False]}
    default_options = "shared=False"
    exports_sources = ["CMakeLists.patch.txt"]
    source_subfolder = "source_subfolder"
    generators = "cmake"

    def requirements(self):
        # make option?
        self.requires("OpenSSL/1.0.2n@conan/stable")

    def source(self):
        file_ext = ".tar.gz" if not self.settings.os == "Windows" else "-win32-src.zip"
        tools.get("http://archive.apache.org/dist/apr/apr-util-" + self.version + file_ext)
        os.rename("apr-util-" + self.version, self.source_subfolder)

        tools.patch(self.source_subfolder, "CMakeLists.patch.txt")

        # # required to fix the FindXXX commands specified by Expat (and openssl?)
        # tools.replace_in_file(self.source_subfolder + "/CMakeLists.txt", "PROJECT(APR-Util C)", '''PROJECT(APR-Util C)
        #     include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)
        #     conan_basic_setup()''')

        # # fix issue in cmakelists - it errors if using a static apr build
        # if self.settings.os == "Windows" and not self.options["apache-apr"].shared:
        #     tools.replace_in_file(self.source_subfolder + "/CMakeLists.txt", "libapr-1.lib", "apr-1.lib")

    def build_linux(self):
        env_build = AutoToolsBuildEnvironment(self)
        env_build.fpic = self.options.shared
        with tools.environment_append(env_build.vars):
            configure_command = "./configure"
            configure_command += " --prefix=" + os.getcwd()
            configure_command += " --with-apr=" + self.deps_cpp_info["apache-apr"].rootpath
            configure_command += " --with-expat=" + self.deps_cpp_info["Expat"].rootpath

            # add with-ssl flag?

            with tools.chdir(self.source_subfolder):
                self.run(configure_command)
                self.run("make -j " + str(max(tools.cpu_count() - 1, 1)))
                self.run("make install")

    def build_windows(self):
        cmake = CMake(self)
        build_target = "libaprutil-1" if self.options.shared == True else "aprutil-1"

        install_folder = self.build_folder + "/buildinstall"
        os.makedirs(install_folder + "/include", exist_ok=True)

        # copy and copy2 will not work due to the permissions issues
        for filename in glob.iglob(self.deps_cpp_info["apache-apr"].include_paths[0] + "/*.h"):
            shutil.copyfile(filename, install_folder + "/include/" + ntpath.basename(filename))

        apr_lib_name = "libapr-1.lib" if self.options["apache-apr"].shared == True else "apr-1.lib"
        os.makedirs(install_folder + "/lib/", exist_ok=True)
        shutil.copyfile(self.deps_cpp_info["apache-apr"].lib_paths[0] + "/" + apr_lib_name,
            install_folder + "/lib/" + apr_lib_name)

        # APR util's CMakeLists.txt file has incorrect references to Expat's vars
        # cmake_lists_file = self.source_folder + "/" + self.source_subfolder + "/CMakeLists.txt"
        # tools.replace_in_file(cmake_lists_file, "EXPAT_INCLUDE_DIRS", "EXPAT_INCLUDE_DIR")
        # tools.replace_in_file(cmake_lists_file, "EXPAT_LIBRARIES", "EXPAT_LIBRARY")

        cmake.definitions["CMAKE_INSTALL_PREFIX"] = install_folder
        cmake.configure(source_folder=self.source_subfolder)
        cmake.build(target=build_target)
        cmake.install()

    def build(self):
        if self.settings.os == "Windows":
            self.build_windows()
        else:
            self.build_linux()

    def package(self):
        base_path = self.build_folder + "/buildinstall/"

        if self.options.shared == True:
            self.copy("*.so*", dst="lib", src=base_path + "lib", keep_path=False)
            self.copy("libaprutil-1.lib", dst="lib", src=base_path + "lib", keep_path=False)
            self.copy("libaprutil-1.dll", dst="bin", src=base_path + "bin", keep_path=False)
        else:
            self.copy("aprutil-1.a", dst="lib", src=base_path + "lib", keep_path=False)
            self.copy("aprutil-1.lib", dst="lib", src=base_path + "lib", keep_path=False)

        self.copy("apu-1-config", dst="bin", src=base_path + "bin", keep_path=False)
        self.copy("*.h", dst="include", src=base_path + "include", keep_path=True)

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)

        if self.settings.os == "Windows" and not self.options.shared:
            self.cpp_info.defines = ["APU_DECLARE_STATIC"]
        # necessary?
        # self.cpp_info.includedirs = ["include/apr-1"]
        # self.cpp_info.libs = ["aprutil-1"]
