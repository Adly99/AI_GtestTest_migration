#ifndef PTP_HANDLER_H
#define PTP_HANDLER_H

#include "LogProxy.h"
#include <chrono>
#include <functional>
#include <memory>

namespace ptph
{

class ptpHandler final
{
public:
    ptpHandler()= default;
    ~ptpHandler()= default;

    virtual void AraTsyncInit();

    static bool GetCurrentSynchronizedTime(uint64_t* current_time);
    static void GetCurrentTime(uint64_t* current_time);

    virtual void AraTsyncDeinit();
};

} // namespace ptph

#endif // PTP_HANDLER_H
