import os
import re

def detect_cxx_standard(project_root):
    """
    Scans CMakeLists.txt in the project root to detect C++ standard (11, 14, 17, 20).
    Returns the standard version as a string, or "17" as a fallback.
    """
    default_std = "17"
    if not project_root or not os.path.isdir(project_root):
        return default_std

    cmake_path = os.path.join(project_root, "CMakeLists.txt")
    if not os.path.exists(cmake_path):
        # Look recursively in immediate subdirectories if not at root
        for item in os.listdir(project_root):
            sub_path = os.path.join(project_root, item)
            if os.path.isdir(sub_path):
                cmake_sub = os.path.join(sub_path, "CMakeLists.txt")
                if os.path.exists(cmake_sub):
                    cmake_path = cmake_sub
                    break
        else:
            return default_std

    try:
        with open(cmake_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Remove CMake comments
        content_clean = re.sub(r"#.*", "", content)

        # Pattern 1: set(CMAKE_CXX_STANDARD 17)
        match_cmake_std = re.search(
            r"set\s*\(\s*CMAKE_CXX_STANDARD\s+(\d+)\s*\)",
            content_clean,
            re.IGNORECASE
        )
        if match_cmake_std:
            return match_cmake_std.group(1)

        # Pattern 2: target_compile_features(... PRIVATE cxx_std_14)
        match_compile_feat = re.search(
            r"cxx_std_(\d+)",
            content_clean,
            re.IGNORECASE
        )
        if match_compile_feat:
            return match_compile_feat.group(1)

        # Pattern 3: CXX_STANDARD 20
        match_target_prop = re.search(
            r"CXX_STANDARD\s+(\d+)",
            content_clean,
            re.IGNORECASE
        )
        if match_target_prop:
            return match_target_prop.group(1)

    except Exception:
        pass

    return default_std
