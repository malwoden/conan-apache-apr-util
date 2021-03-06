from conans import ConanFile, AutoToolsBuildEnvironment, CMake, tools
from conans.errors import ConanException
import os, glob, shutil, ntpath

class ApacheaprutilConan(ConanFile):
    name = "apache-apr-util"
    version = "1.6.1"
    license = "Apache-2.0"
    url = "https://github.com/malwoden/conan-apache-apr-util"
    settings = "os", "compiler", "build_type", "arch"
    requires = "apache-apr/1.6.3@neewill/testing", "expat/2.2.5@bincrafters/stable"
    options = {"shared": [True, False]}
    default_options = "shared=False"
    exports_sources = ["CMakeLists.patch.txt"]
    source_subfolder = "source_subfolder"
    generators = "cmake"

    def requirements(self):
        # make option?
        self.requires("OpenSSL/1.0.2n@conan/stable")

        # cmake file requires patching to support anything other than these settings
        if self.settings.os == "Windows":
            self.options["apache-apr"].shared = self.options.shared
            self.options["expat"].shared = False

        if self.settings.os != "Windows" and self.options.shared:
            raise ConanException("Cannot build shared libs on non-windows platforms")

    def source(self):
        file_ext = ".tar.gz" if not self.settings.os == "Windows" else "-win32-src.zip"
        tools.get("http://archive.apache.org/dist/apr/apr-util-" + self.version + file_ext)
        os.rename("apr-util-" + self.version, self.source_subfolder)

        if self.settings.os == "Windows":
            tools.patch(self.source_subfolder, "CMakeLists.patch.txt")

    def build_unix(self):
        env_build = AutoToolsBuildEnvironment(self)
        env_build.fpic = self.options.shared

        with tools.environment_append(env_build.vars):
            configure_command = "./configure"
            configure_command += " --prefix=" + self.build_folder + "/buildinstall"
            configure_command += " --with-apr=" + self.deps_cpp_info["apache-apr"].rootpath
            configure_command += " --with-expat=" + self.deps_cpp_info["expat"].rootpath
            # How to enable shared util builds
            # configure_command += " --enable-shared=" + ("yes" if self.options.shared else "no")
            # configure_command += " --enable-static=" + ("yes" if not self.options.shared else "no")

            # add with-ssl flag?

            with tools.chdir(self.source_subfolder):
                self.run(configure_command)
                self.run("find ./")
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

        if self.options.shared:
            cmake.definitions["APU_BUILD_SHARED"] = "TRUE"

        cmake.definitions["CMAKE_INSTALL_PREFIX"] = install_folder

        # Cmake file will require patching if these are enabled
        cmake.definitions["APU_HAVE_ODBC"] = "FALSE"
        cmake.definitions["APR_HAS_LDAP"] = "FALSE"

        cmake.configure(source_folder=self.source_subfolder)
        cmake.build(target=build_target)
        cmake.install()

    def build(self):
        if self.settings.os == "Windows":
            self.build_windows()
        else:
            self.build_unix()

    def package(self):
        base_path = self.build_folder + "/buildinstall/"

        if self.options.shared == True:
            self.copy("*.so*", dst="lib", src=base_path + "lib", keep_path=False)
            self.copy("*.dylib*", dst="lib", src=base_path + "lib", keep_path=False)
            self.copy("libaprutil-1.lib", dst="lib", src=base_path + "lib", keep_path=False)
            self.copy("libaprutil-1.dll", dst="bin", src=base_path + "bin", keep_path=False)
        else:
            self.copy("aprutil-1.a", dst="lib", src=base_path + "lib", keep_path=False)
            self.copy("aprutil-1.lib", dst="lib", src=base_path + "lib", keep_path=False)
            self.copy("libaprutil-1.a", dst="lib", src=base_path + "lib", keep_path=False)

        self.copy("apu-1-config", dst="bin", src=base_path + "bin", keep_path=False)
        self.copy("*.h", dst="include", src=base_path + "include", keep_path=True)

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
        if self.settings.os != "Windows":
            self.cpp_info.includedirs = ["include/apr-1"]

        if self.settings.os == "Windows":
            if not self.options.shared:
                self.cpp_info.defines = ["APU_DECLARE_STATIC"]
            else:
                self.cpp_info.defines = ["APU_DECLARE_EXPORT"]
