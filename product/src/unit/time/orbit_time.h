#pragma once

#include <chrono>
#include <cstdint>
#include <string>
#include <vector>

namespace unit::time {

constexpr double kSecPerDay  = 86400.0;
constexpr double kSecPerWeek = 604800.0;

/**
 * UTC/UT1/TAI/TT 的 MJD 表示。
 */
struct MjdTime {
    int64_t day      = 0;
    double  frac_day = 0.0;  // [0,1)
};

/**
 * @contract{TimeSys_4_4_1}
 */
struct UtcMjd {
    MjdTime mjd;
};

/**
 * @contract{TimeSys_4_4_1}
 */
struct Ut1Mjd {
    MjdTime mjd;
};

/**
 * @contract{TimeSys_4_4_1}
 */
struct TaiMjd {
    MjdTime mjd;
};

/**
 * @contract{TimeSys_4_4_1}
 */
struct TtMjd {
    MjdTime mjd;
};

/**
 * @contract{TimeSys_4_4_1}
 */
struct GpstTime {
    uint32_t week = 0;
    double   sec  = 0.0;  // [0,604800)
};

/**
 * @contract{TimeSys_4_4_1}
 */
struct BdtTime {
    uint32_t week = 0;
    double   sec  = 0.0;  // [0,604800)
};

/**
 * UTC 公历时间，仅用于接口。
 * @contract{TimeSys_4_4_2}
 */
struct CivilTime {
    int    year  = 0;
    int    month = 0;
    int    day   = 0;
    int    hour  = 0;
    int    min   = 0;
    double sec   = 0.0;  // UTC 允许 60 表示闰秒
};

enum class TimeStatus {
    kUninitialized,
    kValid,
    kInvalid,
};

enum class TimeError {
    kOk,
    kUninitialized,
    kMissingLeapSeconds,
    kMissingUt1Utc,
    kInvalidCivilTime,
    kOutOfRange,
    kInvalidMjd,
    kInvalidWeekSeconds,
    kTypeMismatch,
};

/**
 * 时间操作返回值。
 */
template <typename T>
struct TimeResult {
    TimeError error = TimeError::kOk;
    T         value{};

    bool ok() const { return error == TimeError::kOk; }

    static TimeResult<T> Ok(const T& v) {
        return TimeResult<T>{TimeError::kOk, v};
    }

    static TimeResult<T> Error(TimeError e) { return TimeResult<T>{e, T{}}; }
};

/**
 * 闰秒表记录：生效日期与 TAI-UTC 秒数。
 */
struct LeapSecondEntry {
    int year          = 0;
    int month         = 0;
    int day           = 0;
    int tai_minus_utc = 0;
};

/**
 * 闰秒表管理与查询。  
 */
class LeapSecondTable {
  public:
    /**
     * 从 CSV 加载闰秒表。
     * @contract{TimeSys_4_6_1}
     */
    static TimeResult<LeapSecondTable> LoadFromCsv(const std::string& path);

    /**
     * 从内存快照构造。
     * @contract{TimeSys_4_6_1}
     */
    static LeapSecondTable FromEntries(
        const std::vector<LeapSecondEntry>& entries);

    /**
     * @brief 返回闰秒表是否已加载有效数据。
     * @contract{TimeSys_4_6_1}
     */
    bool IsValid() const;

    /**
     * 查询某 UTC civil 时刻的 TAI-UTC。
     * @contract{TimeSys_4_4_3}
     */
    TimeResult<int> GetTaiMinusUtcSeconds(const CivilTime& utc) const;

    /**
     * 查询某 UTC MJD 时刻的 TAI-UTC。
     * @contract{TimeSys_4_4_3}
     */
    TimeResult<int> GetTaiMinusUtcSeconds(const UtcMjd& utc) const;

    /**
     * TAI -> UTC civil。
     * @contract{TimeSys_4_6_2}
     */
    TimeResult<CivilTime> TaiToUtcCivil(const TaiMjd& tai) const;

  private:
    std::vector<LeapSecondEntry> entries_;
};

/**
 * 时间尺度管理与显式转换。
 *
 * 物理关系：
 * \f[
 * \mathrm{UTC}=\mathrm{TAI}-\Delta AT,\quad
 * \mathrm{TT}=\mathrm{TAI}+32.184\,\mathrm{s}
 * \f]
 * \f[
 * \mathrm{UT1}=\mathrm{UTC}+(\mathrm{UT1}-\mathrm{UTC})
 * \f]
 * \f[
 * \mathrm{GPST}=\mathrm{TAI}-19\,\mathrm{s},\quad
 * \mathrm{BDT}=\mathrm{GPST}-14\,\mathrm{s}
 * \f]
 */
class TimeSys {
  public:
    /**
     * @brief 构造未初始化状态的时间系统对象。
     * @contract{TimeSys_4_2}
     */
    TimeSys();

    /**
     * 清空状态与缓存。
     * @contract{TimeSys_4_2}
     */
    void Reset();

    /**
     * @contract{TimeSys_4_6_1}
     */
    void SetLeapSecondTable(const LeapSecondTable& table);

    /**
     * @contract{TimeSys_4_4_4}
     */
    void SetUt1MinusUtcSeconds(double ut1_minus_utc_seconds);

    /**
     * 设置指定时间尺  度。
     * @contract{TimeSys_4_1}
     * @contract{TimeSys_4_4_5}
     * @contract{TimeSys_4_7_1}
     */
    template <typename TimeScale>
    TimeError Set(const TimeScale& t) {
        (void)t;
        return TimeError::kTypeMismatch;
    }

    /**
     * 获取指定时间尺度。
     * @contract{TimeSys_4_1}
     * @contract{TimeSys_4_4_5}
     * @contract{TimeSys_4_7_1}
     */
    template <typename TimeScale>
    TimeResult<TimeScale> Get() const {
        return TimeResult<TimeScale>::Error(TimeError::kTypeMismatch);
    }

    /**
     * @contract{TimeSys_4_2}
     */
    TimeStatus Status() const;

    /**
     * 基于 std::chrono::duration 的时间平移（支持 1s/2min/3h 等字面量）。
     * 未初始化时返回无效状态对象。
     * @contract{TimeSys_4_1}
     */
    template <typename Rep, typename Period>
    TimeSys operator+(const std::chrono::duration<Rep, Period>& delta) const {
        std::chrono::duration<double> seconds = delta;
        TimeSys                       result  = *this;
        result.AddSecondsInPlace(seconds.count());
        return result;
    }

    /**
     * 基于 std::chrono::duration 的时间平移（支持 1s/2min/3h 等字面量）。
     * 未初始化时返回无效状态对象。
     * @contract{TimeSys_4_1}
     */
    template <typename Rep, typename Period>
    TimeSys operator-(const std::chrono::duration<Rep, Period>& delta) const {
        std::chrono::duration<double> seconds = delta;
        TimeSys                       result  = *this;
        result.AddSecondsInPlace(-seconds.count());
        return result;
    }

    /**
     * 原地加时间（支持 1s/2min/3h 等字面量）。
     * 未初始化时置为无效状态。
     * @contract{TimeSys_4_1}
     */
    template <typename Rep, typename Period>
    TimeSys& operator+=(const std::chrono::duration<Rep, Period>& delta) {
        std::chrono::duration<double> seconds = delta;
        return AddSecondsInPlace(seconds.count());
    }

    /**
     * 原地减时间（支持 1s/2min/3h 等字面量）。
     * 未初始化时置为无效状态。
     * @contract{TimeSys_4_1}
     */
    template <typename Rep, typename Period>
    TimeSys& operator-=(const std::chrono::duration<Rep, Period>& delta) {
        std::chrono::duration<double> seconds = delta;
        return AddSecondsInPlace(-seconds.count());
    }

    /**
     * 计算两个 TimeSys 的 TAI 秒差（this - other）。
     * 任一未初始化则返回错误。
     * @contract{TimeSys_4_1}
     * @contract{TimeSys_4_7_1}
     */
    TimeResult<std::chrono::duration<double>> operator-(
        const TimeSys& other) const;

  private:
    /**
     * @brief 以 UTC civil 输入设置内部 TAI 状态。
     */
    TimeError SetUtcCivil(const CivilTime& utc);
    /**
     * @brief 以 UTC MJD 输入设置内部 TAI 状态。
     */
    TimeError SetUtcMjd(const UtcMjd& utc);
    /**
     * @brief 以 TAI MJD 输入设置内部状态。
     */
    TimeError SetTaiMjd(const TaiMjd& tai);
    /**
     * @brief 以 TT MJD 输入设置内部状态。
     */
    TimeError SetTtMjd(const TtMjd& tt);
    /**
     * @brief 以 GPST 周秒输入设置内部状态。
     */
    TimeError SetGpst(const GpstTime& gpst);
    /**
     * @brief 以 BDT 周秒输入设置内部状态。
     */
    TimeError SetBdt(const BdtTime& bdt);

    /**
     * @brief 以 UTC MJD 形式读取当前时刻。
     */
    TimeResult<UtcMjd>    GetUtcMjd() const;
    /**
     * @brief 以 UTC Civil 形式读取当前时刻。
     */
    TimeResult<CivilTime> GetUtcCivil() const;
    /**
     * @brief 以 UT1 MJD 形式读取当前时刻。
     */
    TimeResult<Ut1Mjd>    GetUt1Mjd() const;
    /**
     * @brief 以 TAI MJD 形式读取当前时刻。
     */
    TimeResult<TaiMjd>    GetTaiMjd() const;
    /**
     * @brief 以 TT MJD 形式读取当前时刻。
     */
    TimeResult<TtMjd>     GetTtMjd() const;
    /**
     * @brief 以 GPST 周秒形式读取当前时刻。
     */
    TimeResult<GpstTime>  GetGpst() const;
    /**
     * @brief 以 BDT 周秒形式读取当前时刻。
     */
    TimeResult<BdtTime>   GetBdt() const;

    /**
     * @brief 检查 MJD 表示是否合法。
     */
    static bool IsMjdValid(const MjdTime& mjd);

    /**
     * @brief 归一化 MJD 日与秒到标准区间。
     */
    static MjdTime NormalizeMjdSeconds(int64_t day, double seconds);

    /**
     * @brief 检查 UTC 相关依赖是否齐备。
     */
    TimeError EnsureReadyForUtc() const;
    /**
     * @brief 检查 UT1 相关依赖是否齐备。
     */
    TimeError EnsureReadyForUt1() const;

    /**
     * @brief 对内部时间状态执行秒级原地平移。
     */
    TimeSys& AddSecondsInPlace(double seconds);

    TimeStatus status_      = TimeStatus::kUninitialized;
    bool       initialized_ = false;

    LeapSecondTable leap_seconds_;
    bool            has_leap_seconds_ = false;

    double ut1_minus_utc_seconds_ = 0.0;
    bool   has_ut1_minus_utc_     = false;

    TaiMjd tai_{};
};

/// \cond DOXYGEN_SKIP
// 显式特化声明：避免包含头文件的翻译单元实例化默认模板，确保链接到 .cpp 中的实现。
// 否则在部分平台（如 Fedora/GCC）上会使用默认模板（返回 kTypeMismatch）而非正确实现。
template <>
TimeError TimeSys::Set<CivilTime>(const CivilTime& t);
template <>
TimeError TimeSys::Set<UtcMjd>(const UtcMjd& t);
template <>
TimeError TimeSys::Set<Ut1Mjd>(const Ut1Mjd& t);
template <>
TimeError TimeSys::Set<TaiMjd>(const TaiMjd& t);
template <>
TimeError TimeSys::Set<TtMjd>(const TtMjd& t);
template <>
TimeError TimeSys::Set<GpstTime>(const GpstTime& t);
template <>
TimeError TimeSys::Set<BdtTime>(const BdtTime& t);
template <>
TimeResult<CivilTime> TimeSys::Get<CivilTime>() const;
template <>
TimeResult<UtcMjd> TimeSys::Get<UtcMjd>() const;
template <>
TimeResult<Ut1Mjd> TimeSys::Get<Ut1Mjd>() const;
template <>
TimeResult<TaiMjd> TimeSys::Get<TaiMjd>() const;
template <>
TimeResult<TtMjd> TimeSys::Get<TtMjd>() const;
template <>
TimeResult<GpstTime> TimeSys::Get<GpstTime>() const;
template <>
TimeResult<BdtTime> TimeSys::Get<BdtTime>() const;
/// \endcond

}  // namespace unit::time
