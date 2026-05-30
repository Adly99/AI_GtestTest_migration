#ifndef CODING_RBC_INTERFACES_H
#define CODING_RBC_INTERFACES_H
// Original include guard - preserved.

#include "gmock/gmock.h"
#include "gtest/gtest.h"
// GMock and GTest includes added.

#include "sys.h" // Original include - preserved.
#include "PVISParamCFG.h" // Original include - preserved.

namespace config
{
// Original namespace - preserved.

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

    MOCK_METHOD(void, GetPvisCfgData, (struct PVISParamCFG& pvis_rbc_data));
    MOCK_METHOD(void, GetCarInfoData, (struct carInfo& car_info_rbc_data));
    MOCK_METHOD(bool, IsCarInfoCfgUpdated, ());

private:
    // Private constructor and destructor to enforce singleton pattern.
    CodingRbcInterfacesMock(void) = default;
    ~CodingRbcInterfacesMock(void) = default;
};

// The implementation of each original free function is replaced to call the mock instance, making it testable.
inline void GetPvisCfgData(struct PVISParamCFG& pvis_rbc_data) {
    CodingRbcInterfacesMock::getInstance().GetPvisCfgData(pvis_rbc_data);
}

// The implementation of each original free function is replaced to call the mock instance, making it testable.
inline void GetCarInfoData(struct carInfo& car_info_rbc_data) {
    CodingRbcInterfacesMock::getInstance().GetCarInfoData(car_info_rbc_data);
}

// The implementation of each original free function is replaced to call the mock instance, making it testable.
inline bool IsCarInfoCfgUpdated() {
    return CodingRbcInterfacesMock::getInstance().IsCarInfoCfgUpdated();
}

// constexpr function - preserved.
// This function is evaluated at compile-time and cannot be mocked.
constexpr std::uint32_t GetExtrinsicsSerlSize()
{
    return 100;
}

} // namespace config

#endif // CODING_RBC_INTERFACES_H
