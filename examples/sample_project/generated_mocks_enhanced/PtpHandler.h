#ifndef PTP_HANDLER_H
#define PTP_HANDLER_H
// Original include guard - preserved.

#include "gmock/gmock.h"
#include "gtest/gtest.h"
// GMock and GTest includes added.

#include "LogProxy.h" // Original include - preserved.
#include <chrono> // Original include - preserved.
#include <functional> // Original include - preserved.
#include <memory> // Original include - preserved.

namespace ptph
{
// Original namespace - preserved.

// A companion mock class is generated to allow mocking of static methods.
class ptpHandlerMock
{
public:
    static ptpHandlerMock& getInstance(void)
    {
        static ptpHandlerMock instance;
        return instance;
    }

    MOCK_METHOD(bool, GetCurrentSynchronizedTime, (uint64_t* current_time));
    MOCK_METHOD(void, GetCurrentTime, (uint64_t* current_time));

private:
    ptpHandlerMock(void) = default;
    ~ptpHandlerMock(void) = default;
};

// Original class definition - transformed for GMock.
class MockptpHandler : public ptpHandler
{
public:
    // Original lifecycle method - preserved.
    ptpHandler()= default;

    // Original lifecycle method - preserved.
    ~ptpHandler()= default;

    // Static method - preserved and delegated to the singleton mock.
    static bool GetCurrentSynchronizedTime(uint64_t* current_time)
    {
        return ptpHandlerMock::getInstance().GetCurrentSynchronizedTime(current_time);
    }

    // Static method - preserved and delegated to the singleton mock.
    static void GetCurrentTime(uint64_t* current_time)
    {
        ptpHandlerMock::getInstance().GetCurrentTime(current_time);
    }

    // Mock for the full method signature.
    MOCK_METHOD(void, AraTsyncInit, (), (override));

    // Mock for the full method signature.
    MOCK_METHOD(void, AraTsyncDeinit, (), (override));

    // Private section and all its contents removed for mock generation.
};

} // namespace ptph

#endif // PTP_HANDLER_H
