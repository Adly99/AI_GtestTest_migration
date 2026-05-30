# **Enhanced GTest/GMock Generation Workflow**

This document provides a detailed, step-by-step automated workflow for transforming C++ header files into high-quality GTest/GMock mock classes. The process is designed to handle various C++ features, including static class methods and free functions in a namespace, and provides clear configuration options.

### **Core Principles**

* **Automation:** Minimize manual editing by systematically transforming the original header.  
* **Interface Focus:** The final mock exposes only the public interface needed for testing.  
* **Clarity:** Generated code is heavily commented to trace back to the original structure.

### **Constraints and Guidelines**

To ensure the best results from this automated workflow, please consider the following:

#### **Constraints (What the workflow may not handle perfectly):**

* **Complex Macros:** Preprocessor macros that generate class members or complex control flow can interfere with parsing. The workflow is designed for standard C++ syntax.  
* **Preprocessor Directives:** Conditional compilation (\#if, \#ifdef) within a class definition is not fully analyzed and may lead to incomplete mocks. All code within the class body is assumed to be active.  
* **Private/Protected Nested Types:** Nested classes or structs in private or protected sections are not supported, as these sections are removed entirely.  
* **Heavily Templated Code:** While simple templated methods are preserved, complex template metaprogramming may not be transformed correctly.  
* constexpr **functions:** These functions are evaluated at compile-time and cannot be mocked; they will be preserved as-is.

#### **Guidelines (For optimal results):**

* **Clean Header Design:** Ensure your header files have a clear separation between the public interface and private implementation details.  
* **Standard Syntax:** Adhere to standard C++ class and method declarations.  
* **One Class Per Header:** While not mandatory, the process is most reliable when a single primary class is defined per header file.

### **Workflow Steps:**

**Step 0: User Input & Configuration**

* **Goal:** To acquire the target header files and define the output location.  
* **Action:** The system will prompt the user for the following inputs.  
* **Inputs:**  
  1. **Header File(s):** Select one or more C++ header files to be transformed (e.g., \["PtpHandler.h", "coding\_rbc\_interfaces.h"\]). The system will ensure all selected files are processed.  
  2. **Output Path:** Specify the directory where the generated mock files will be saved.  
     * **Default:** ./mocks/  
     * **Example:** ../tests/mocks/  
* **Output:** The C++ header files are loaded and the output destination is confirmed.

**Step 1: System Configuration**

* **Goal:** To establish the AI's role and the overall objective.  
* **Action:** The AI model is configured with system-level instructions.  
* **Instructions:** "You are an expert C++ GTest/GMock assistant. Your task is to systematically transform given C++ header files into corresponding mock headers, paying special attention to static methods and free functions, and preserving the original structure where appropriate."  
* **Output:** A configured AI assistant ready to execute the transformation pipeline.

**Step 2: Header and Include Processing**

* **Goal:** To set up the basic file structure, preserving original include guards and injecting the necessary GMock/GTest headers.  
* **Input:** An original C++ header file.  
* **Transformations:**  
  1. **Preserve Include Guards:** The original \#ifndef / \#define / \#endif directives are preserved. The include guard name may be updated to reflect it's a mock (e.g.,without adding \_MOCK or adding any anything should be teh same). A comment is added: // Original include guard \- preserved.  
  2. **Inject GMock/GTest Headers:** The following lines are inserted immediately after the \#define directive:

```

#include "gmock/gmock.h"
#include "gtest/gtest.h"
// GMock and GTest includes added.

```

  5.   
     **Preserve Original Includes:** All original \#include directives are retained. A comment is added to each: // Original include \- preserved.  
* **Output:** A header file with foundational includes and guards correctly configured.

**Step 3: Structural Annotation (Namespaces & Classes)**

* **Goal:** To identify and annotate the core code structures.  
* **Input:** The output from Step 2\.  
* **Transformations:**  
  1. **Preserve Namespaces:** Any namespaces are preserved. A comment is added: // Original namespace \- preserved.  
  2. **Annotate Class Definitions:** The original class definition is preserved with a comment: // Original class definition \- to be transformed for GMock.  
* **Output:** The header file with key structural elements annotated.

**Step 4: Handling Static Class Methods (Singleton Mock Pattern)**

* **Goal:** To create a mockable interface for static methods within a class by introducing a companion singleton mock class.  
* **Input:** The output from Step 3\.  
* **Transformations:**  
  1. **Identify Static Methods:** All public static methods within a class are identified.  
  2. **Create Companion Mock Class:** A new class is created *before* the original class, named with a Mock suffix (e.g., PtpHandlerMock).  
  3. **Delegate Original Static Calls:** The body of each original public static method is replaced with a call to the corresponding method on the singleton mock instance.  
* Comprehensive Example \#1 (Static Class Methods):  
  This example shows the final state of PtpHandler.h after all workflow steps have been applied.

```

#ifndef PTP_HANDLER_H
#define PTP_HANDLER_H
// Original include guard - preserved.

#include "gmock/gmock.h"
#include "gtest/gtest.h"
// GMock and GTest includes added.

#include "LogProxy.h" // Original include - preserved.
#include <chrono>     // Original include - preserved.
#include <functional> // Original include - preserved.
#include <memory>     // Original include - preserved.

namespace ptph
{
// Original namespace - preserved.

// A companion mock class is generated to allow mocking of static methods.
class PtpHandlerMock
{
public:
    static PtpHandlerMock& getInstance(void) { /* ... */ }
    MOCK_METHOD(bool, GetCurrentSynchronizedTime, (uint64_t*));
    MOCK_METHOD(void, GetCurrentTime, (uint64_t*));
private:
    PtpHandlerMock(void) = default;
    ~PtpHandlerMock(void) = default;
};

// Original class definition - transformed for GMock.
class ptpHandler final
{
public:
    ptpHandler()= default;
    // ... deleted constructors/operators preserved ...
    ~ptpHandler()= default;

    MOCK_METHOD(void, AraTsyncInit, ());

    // Static method - preserved and delegated to the singleton mock.
    static bool GetCurrentSynchronizedTime(uint64_t* current_time)
    {
        return PtpHandlerMock::getInstance().GetCurrentSynchronizedTime(current_time);
    }
    // ... other static and templated methods preserved ...
    MOCK_METHOD(void, AraTsyncDeinit, ());
};
} // namespace ptph
#endif // PTP_HANDLER_H

```

*   
  **Output:** A header where static class methods are made testable via a singleton mock delegate.

**Step 4a: Handling Free Functions in a Namespace (Singleton Mock Pattern)**

* **Goal:** To create a mockable interface for free functions within a namespace.  
* **Input:** A header file containing free functions within a namespace.  
* **Transformations:**  
  1. **Identify Free Functions:** All functions within the namespace (not belonging to a class) are identified.  
  2. **Create a Single Mock Class:** A new singleton class is created inside the namespace. The class name is derived from the header file (e.g., CodingRbcInterfacesMock).  
  3. **Convert Functions to Mocks:** For each original free function, a corresponding MOCK\_METHOD is created inside the new mock class.  
  4. **Delegate Original Functions:** The original free function declarations are replaced with new function definitions that delegate the call to the corresponding method on the singleton mock instance. constexpr functions are preserved as-is.  
* Comprehensive Example \#2 (Free Functions):  
  This shows the transformation of coding\_rbc\_interfaces.h.

```

#ifndef CODING_RBC_INTERFACES_H
#define CODING_RBC_INTERFACES_H
// Original include guard - preserved.

#include "gmock/gmock.h"
#include "gtest/gtest.h"
// GMock and GTest includes added.

// Original includes - preserved.
#include "sys.h"
#include "PVISParamCFG.h"
// ... other includes preserved ...

namespace config
{
// A companion mock class is generated to allow mocking of free functions.
// This singleton class provides a single point of access for tests to set
// expectations on function calls.
class CodingRbcInterfacesMock
{
public:
    // Provides global access to the single instance of this mock class.
    static CodingRbcInterfacesMock& getInstance(void)
    {
        static CodingRbcInterfacesMock instance;
        return instance;
    }

    // Mocks corresponding to the original free functions.
    MOCK_METHOD(void, GetPvisCfgData, (struct PVISParamCFG& pvis_rbc_data));
    MOCK_METHOD(void, GetCarInfoData, (struct carInfo& car_info_rbc_data));
    MOCK_METHOD(bool, IsCarInfoCfgUpdated, ());
    // ... all other functions are converted to MOCK_METHOD ...

private:
    // Private constructor and destructor to enforce singleton pattern.
    CodingRbcInterfacesMock(void) = default;
    ~CodingRbcInterfacesMock(void) = default;
};

// The implementation of each original free function is replaced to call the mock instance, making it testable.
inline void GetPvisCfgData(struct PVISParamCFG& pvis_rbc_data) {
    CodingRbcInterfacesMock::getInstance().GetPvisCfgData(pvis_rbc_data);
}
inline void GetCarInfoData(struct carInfo& car_info_rbc_data) {
    CodingRbcInterfacesMock::getInstance().GetCarInfoData(car_info_rbc_data);
}
inline bool IsCarInfoCfgUpdated(void) {
    return CodingRbcInterfacesMock::getInstance().IsCarInfoCfgUpdated();
}
// ... all other functions are replaced with delegations ...

// constexpr function - preserved.
// This function is evaluated at compile-time and cannot be mocked.
constexpr std::uint32_t GetExtrinsicsSerlSize()
{
    return static_cast<std::uint32_t>(sizeof(CameraMgr_v2::BMWNominals));
}
}; // namespace config

#endif // CODING_RBC_INTERFACES_H
```

*   
  **Output:** A header where free functions are made testable via a singleton mock delegate.

**Step 5: Mocking Public Instance Methods**

* **Goal:** To convert all relevant public instance methods of a class into GMock's MOCK\_METHOD macros.  
* **Input:** The output from Step 4\.  
* **Transformations:**  
  1. **Method Selection:** All public instance (non-static) methods are targeted, **excluding** constructors and destructors.  
  2. MOCK\_METHOD **Conversion:** Each selected method is replaced with a MOCK\_METHOD macro.  
* **Output:** A header where the mockable public API has been transformed into GMock macros.

**Step 5a: Handling Methods with Default Arguments**

* **Goal:** To correctly mock methods that have default arguments while preserving the original calling signature for client code.  
* **Input:** A public method with one or more default arguments.  
* **Transformations:**  
  * **Create Full** MOCK\_METHOD**:** A MOCK\_METHOD is generated that includes the complete signature of the original method, including all arguments (even those with default values). For const methods, the const qualifier is added as the 4th parameter to the MOCK\_METHOD macro.  
  * **Create Overloaded Wrapper:** A non-virtual overloaded function is created that matches the signature of the original function *without* the default arguments. The body of this wrapper function calls the fully-qualified mocked method, explicitly passing the original default value. This ensures that existing code calling the method without the optional argument continues to compile and now routes through the mock.  
* **Comprehensive Examples:**  
  * **Example \#1 (Non-const method with default enum value):**  
    * **Input:**

```

NvmState TriggerNvmSync(const KvsType target_kvs_to_save = KvsType::NormalKvs);

```

    *   
      **Output:**

```

// Mock for the full method signature.
MOCK_METHOD(NvmState, TriggerNvmSync, (const KvsType target_kvs_to_save));

// Overloaded wrapper to handle calls using the default argument.
NvmState TriggerNvmSync()
{
    return TriggerNvmSync(KvsType::NormalKvs);
};

```

  *   
    **Example \#2 (Const method with default enum value):**  
    * **Input:**

```

void getCurrentXZZ(camera::Extrinsics &xzz, camera::CamId::P2Id cam_id, CALIBRATION_TYPE calib_type = CALIBRATION_TYPE_SPR) const;

```

    *   
      **Output:**

```

// Mock for the full method signature, including the 'const' qualifier.
MOCK_METHOD(void, getCurrentXZZ, (camera::Extrinsics &xzz, camera::CamId::P2Id cam_id, CALIBRATION_TYPE calib_type), (const));

// Overloaded wrapper to handle calls using the default argument.
void getCurrentXZZ(camera::Extrinsics &xzz, camera::CamId::P2Id cam_id) const
{
    // The original default value is preserved in the wrapper call.
    getCurrentXZZ(xzz, cam_id, CALIBRATION_TYPE_SPR);
};

```

*   
  **Output:** Mock methods that are compatible with default arguments and provide wrappers for backward compatibility.

**Step 6: Preserving Constructors, Destructors, and Operators**

* **Goal:** To ensure the mock object's lifecycle methods and special operators are preserved.  
* **Input:** The output from Step 5\.  
* **Transformations:**  
  1. **Preserve Constructors/Destructor:** All constructors and the destructor are preserved exactly, including \= default, \= delete, and the virtual keyword on the destructor. Comments are added: // Original constructor \- preserved., // Original virtual destructor \- preserved., etc.  
  2. **Preserve Assignment/Move Operators:** Copy/move constructors and assignment operators are preserved with comments.  
* **Output:** A mock header with its essential lifecycle methods intact.

**Step 7: Removing Non-Public Sections**

* **Goal:** To strip the class of all implementation details, leaving only the public interface.  
* **Input:** The output from Step 6\.  
* **Transformations:**  
  1. **Delete Private Section:** The private: access specifier and all its contents are removed. A placeholder comment is inserted: // Private section and all its contents removed for mock generation.  
  2. **Delete Protected Section:** The protected: section is similarly removed. A comment is inserted: // Protected section and all its contents removed for mock generation.  
* **Output:** A clean header file containing only the public, mockable interface.

**Step 8: Preserving Ancillary Public Members**

* **Goal:** To preserve all other necessary public code elements that are not mockable methods.  
* **Input:** The output from Step 7\.  
* **Transformations:** The following elements are preserved with descriptive comments:  
  * **Templated Methods:** // Templated method \- preserved.  
  * **Public Member Variables:** // Public member \- preserved.  
  * **Other Declarations:** typedef, enum, using, and friend declarations are kept with comments like // Original typedef \- preserved.  
* **Output:** The fully transformed mock header content.

**Step 9: Final Output Generation**

* **Goal:** To save the completed mock header(s) to the specified output path.  
* **Input:** The final, transformed C++ content and the user-defined output path.  
* **Action:**  
  1. The transformed C++ content for each header is finalized.  
  2. Each result is saved to a file with its original name inside the directory specified in **Step 0**.  
* **Final Output:** One or more complete, self-contained C++ mock header files in the target directory (e.g., ./mocks/PtpHandler.h).

