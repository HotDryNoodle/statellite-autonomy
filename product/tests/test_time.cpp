/**
 * @file product/tests/test_time.cpp
 * @ingroup tests
 * @brief TimeSys 合同条款的单元测试验证（GTest）。
 */
#include <gtest/gtest.h>

#include <chrono>
#include <cmath>
#include <filesystem>
#include <string>

#include "orbit_time.h"

namespace {

std::string FindDataFile(const std::string& filename) {
    namespace fs = std::filesystem;
    fs::path dir = fs::current_path();
    while (true) {
        fs::path eop_candidate = dir / "data" / "eop" / filename;
        if (fs::exists(eop_candidate)) { return eop_candidate.string(); }
        fs::path candidate = dir / "data" / filename;
        if (fs::exists(candidate)) { return candidate.string(); }
        if (!dir.has_parent_path()) { break; }
        fs::path parent = dir.parent_path();
        if (parent == dir) { break; }
        dir = parent;
    }
    return "";
}

bool LoadLeapSeconds(unit::time::LeapSecondTable& table) {
    std::string path = FindDataFile("leap_seconds.csv");
    if (path.empty()) { return false; }
    auto result = unit::time::LeapSecondTable::LoadFromCsv(path);
    if (!result.ok()) { return false; }
    table = result.value;
    return true;
}

double MjdDiffSeconds(const unit::time::MjdTime& a,
                      const unit::time::MjdTime& b) {
    int    day_diff  = a.day - b.day;
    double frac_diff = a.frac_day - b.frac_day;
    return static_cast<double>(day_diff) * unit::time::kSecPerDay +
           frac_diff * unit::time::kSecPerDay;
}

constexpr double kTimeToleranceSec = 1e-12;

}  // namespace

/**
 * @verify{TimeSys_6_1}
 * @covers{unit::time::TimeSys::Set}
 */
TEST(TimeSysRoundTrip, UtcTtUtc) {
    unit::time::LeapSecondTable leap_seconds;
    ASSERT_TRUE(LoadLeapSeconds(leap_seconds));

    unit::time::TimeSys time;
    time.SetLeapSecondTable(leap_seconds);
    unit::time::CivilTime utc{2018, 1, 1, 0, 0, 0.0};
    ASSERT_EQ(time.Set(utc), unit::time::TimeError::kOk);

    auto tt = time.Get<unit::time::TtMjd>();
    ASSERT_TRUE(tt.ok());
    auto utc_mjd = time.Get<unit::time::UtcMjd>();
    ASSERT_TRUE(utc_mjd.ok());

    unit::time::TimeSys time2;
    time2.SetLeapSecondTable(leap_seconds);
    ASSERT_EQ(time2.Set(tt.value), unit::time::TimeError::kOk);
    auto utc_back = time2.Get<unit::time::UtcMjd>();
    ASSERT_TRUE(utc_back.ok());

    double diff_sec =
        std::fabs(MjdDiffSeconds(utc_back.value.mjd, utc_mjd.value.mjd));
    EXPECT_LT(diff_sec, kTimeToleranceSec);
}

/**
 * @verify{TimeSys_6_1}
 * @covers{unit::time::TimeSys::Get}
 */
TEST(TimeSysRoundTrip, UtcGpstUtc) {
    unit::time::LeapSecondTable leap_seconds;
    ASSERT_TRUE(LoadLeapSeconds(leap_seconds));

    unit::time::TimeSys time;
    time.SetLeapSecondTable(leap_seconds);
    unit::time::CivilTime utc{2020, 5, 2, 12, 0, 0.0};
    ASSERT_EQ(time.Set(utc), unit::time::TimeError::kOk);

    auto gpst = time.Get<unit::time::GpstTime>();
    ASSERT_TRUE(gpst.ok());

    unit::time::TimeSys time2;
    time2.SetLeapSecondTable(leap_seconds);
    ASSERT_EQ(time2.Set(gpst.value), unit::time::TimeError::kOk);
    auto utc_back = time2.Get<unit::time::UtcMjd>();
    ASSERT_TRUE(utc_back.ok());

    auto utc_mjd = time.Get<unit::time::UtcMjd>();
    ASSERT_TRUE(utc_mjd.ok());
    double diff_sec =
        std::fabs(MjdDiffSeconds(utc_back.value.mjd, utc_mjd.value.mjd));
    EXPECT_LT(diff_sec, kTimeToleranceSec);
}

/**
 * @verify{TimeSys_6_1}
 * @covers{unit::time::TimeSys::operator-}
 */
TEST(TimeSysRoundTrip, GpstBdtGpst) {
    unit::time::TimeSys  time;
    unit::time::GpstTime gpst{2234, 12345.678};
    ASSERT_EQ(time.Set(gpst), unit::time::TimeError::kOk);

    auto bdt = time.Get<unit::time::BdtTime>();
    ASSERT_TRUE(bdt.ok());

    unit::time::TimeSys time2;
    ASSERT_EQ(time2.Set(bdt.value), unit::time::TimeError::kOk);
    auto gpst_back = time2.Get<unit::time::GpstTime>();
    ASSERT_TRUE(gpst_back.ok());

    double diff_sec = std::fabs(gpst_back.value.sec - gpst.sec) +
                      std::fabs(static_cast<double>(gpst_back.value.week) -
                                static_cast<double>(gpst.week)) *
                          unit::time::kSecPerWeek;
    EXPECT_LT(diff_sec, 1e-7);

    auto diff = time - time2;
    ASSERT_TRUE(diff.ok());
    EXPECT_LT(diff.value.count(), kTimeToleranceSec);
}

/**
 * @verify{TimeSys_6_3}
 * @covers{unit::time::TimeSys::Set}
 */
TEST(TimeSysLeapSecond, Boundary2015) {
    unit::time::LeapSecondTable leap_seconds;
    ASSERT_TRUE(LoadLeapSeconds(leap_seconds));

    unit::time::TimeSys time1;
    time1.SetLeapSecondTable(leap_seconds);
    ASSERT_EQ(time1.Set(unit::time::CivilTime{2015, 6, 30, 23, 59, 59.0}),
              unit::time::TimeError::kOk);
    auto tai1 = time1.Get<unit::time::TaiMjd>();
    ASSERT_TRUE(tai1.ok());

    unit::time::TimeSys time2;
    time2.SetLeapSecondTable(leap_seconds);
    ASSERT_EQ(time2.Set(unit::time::CivilTime{2015, 6, 30, 23, 59, 60.0}),
              unit::time::TimeError::kOk);
    auto tai2 = time2.Get<unit::time::TaiMjd>();
    ASSERT_TRUE(tai2.ok());

    unit::time::TimeSys time3;
    time3.SetLeapSecondTable(leap_seconds);
    ASSERT_EQ(time3.Set(unit::time::CivilTime{2015, 7, 1, 0, 0, 0.0}),
              unit::time::TimeError::kOk);
    auto tai3 = time3.Get<unit::time::TaiMjd>();
    ASSERT_TRUE(tai3.ok());

    double dt_1 = MjdDiffSeconds(tai2.value.mjd, tai1.value.mjd);
    double dt_2 = MjdDiffSeconds(tai3.value.mjd, tai1.value.mjd);
    EXPECT_NEAR(dt_1, 2.0, kTimeToleranceSec);
    EXPECT_NEAR(dt_2, 2.0, kTimeToleranceSec);
    EXPECT_NEAR(MjdDiffSeconds(tai3.value.mjd, tai2.value.mjd), 0.0,
                kTimeToleranceSec);
}

/**
 * @verify{TimeSys_6_2}
 * @covers{unit::time::TimeSys::Set}
 */
TEST(TimeSysLeapSecond, InvalidLeapSecondRejected) {
    unit::time::LeapSecondTable leap_seconds;
    ASSERT_TRUE(LoadLeapSeconds(leap_seconds));

    unit::time::TimeSys time;
    time.SetLeapSecondTable(leap_seconds);
    auto err = time.Set(unit::time::CivilTime{2015, 7, 2, 23, 59, 60.0});
    EXPECT_EQ(err, unit::time::TimeError::kInvalidCivilTime);
}

/**
 * @verify{TimeSys_6_4}
 * @covers{unit::time::TimeSys::SetUt1MinusUtcSeconds}
 */
TEST(TimeSysUt1, RequiresUt1MinusUtc) {
    unit::time::LeapSecondTable leap_seconds;
    ASSERT_TRUE(LoadLeapSeconds(leap_seconds));

    unit::time::TimeSys time;
    time.SetLeapSecondTable(leap_seconds);
    ASSERT_EQ(time.Set(unit::time::CivilTime{2019, 3, 1, 0, 0, 0.0}),
              unit::time::TimeError::kOk);

    auto ut1_before = time.Get<unit::time::Ut1Mjd>();
    ASSERT_FALSE(ut1_before.ok());
    EXPECT_EQ(ut1_before.error, unit::time::TimeError::kMissingUt1Utc);

    time.SetUt1MinusUtcSeconds(0.334);
    auto ut1_after = time.Get<unit::time::Ut1Mjd>();
    ASSERT_TRUE(ut1_after.ok());
    auto utc = time.Get<unit::time::UtcMjd>();
    ASSERT_TRUE(utc.ok());

    double diff_sec = MjdDiffSeconds(ut1_after.value.mjd, utc.value.mjd);
    EXPECT_NEAR(diff_sec, 0.334, kTimeToleranceSec);
}

/**
 * @verify{TimeSys_6_5}
 * @covers{unit::time::TimeSys::Get}
 */
TEST(TimeSysErrors, TypeMismatch) {
    struct DummyTimeScale {
        int value = 0;
    };

    unit::time::TimeSys time;
    DummyTimeScale      dummy{};
    EXPECT_EQ(time.Set(dummy), unit::time::TimeError::kTypeMismatch);
    auto res = time.Get<DummyTimeScale>();
    ASSERT_FALSE(res.ok());
    EXPECT_EQ(res.error, unit::time::TimeError::kTypeMismatch);
}

/**
 * @verify{TimeSys_6_8}
 * @covers{unit::time::TimeSys::Set}
 */
TEST(TimeSysErrors, InvalidInputsFail) {
    unit::time::TimeSys time;
    auto err = time.Set(unit::time::CivilTime{2019, 2, 30, 0, 0, 0.0});
    EXPECT_EQ(err, unit::time::TimeError::kInvalidCivilTime);

    unit::time::LeapSecondTable leap_seconds;
    ASSERT_TRUE(LoadLeapSeconds(leap_seconds));
    time.Reset();
    time.SetLeapSecondTable(leap_seconds);
    err = time.Set(unit::time::UtcMjd{unit::time::MjdTime{60000, 1.1}});
    EXPECT_EQ(err, unit::time::TimeError::kInvalidMjd);

    time.Reset();
    err = time.Set(unit::time::GpstTime{100, unit::time::kSecPerWeek});
    EXPECT_EQ(err, unit::time::TimeError::kInvalidWeekSeconds);
}

/**
 * @verify{TimeSys_6_8}
 * @covers{unit::time::TimeSys::Set}
 */
TEST(TimeSysErrors, MissingLeapSecondsAndOutOfRange) {
    unit::time::TimeSys time;
    auto err = time.Set(unit::time::CivilTime{2019, 1, 1, 0, 0, 0.0});
    EXPECT_EQ(err, unit::time::TimeError::kMissingLeapSeconds);

    unit::time::LeapSecondTable leap_seconds;
    ASSERT_TRUE(LoadLeapSeconds(leap_seconds));
    time.Reset();
    time.SetLeapSecondTable(leap_seconds);
    err = time.Set(unit::time::CivilTime{1960, 1, 1, 0, 0, 0.0});
    EXPECT_EQ(err, unit::time::TimeError::kOutOfRange);
}

/**
 * @verify{TimeSys_6_6}
 * @covers{unit::time::TimeSys::Get}
 */
TEST(TimeSysContinuity, ContinuousScalesMonotonic) {
    unit::time::LeapSecondTable leap_seconds;
    ASSERT_TRUE(LoadLeapSeconds(leap_seconds));

    unit::time::TimeSys time1;
    time1.SetLeapSecondTable(leap_seconds);
    ASSERT_EQ(time1.Set(unit::time::CivilTime{2018, 6, 1, 0, 0, 0.0}),
              unit::time::TimeError::kOk);
    auto tai1  = time1.Get<unit::time::TaiMjd>();
    auto tt1   = time1.Get<unit::time::TtMjd>();
    auto gpst1 = time1.Get<unit::time::GpstTime>();
    ASSERT_TRUE(tai1.ok() && tt1.ok() && gpst1.ok());

    unit::time::TimeSys time2;
    time2.SetLeapSecondTable(leap_seconds);
    ASSERT_EQ(time2.Set(unit::time::CivilTime{2018, 6, 1, 0, 0, 10.0}),
              unit::time::TimeError::kOk);
    auto tai2  = time2.Get<unit::time::TaiMjd>();
    auto tt2   = time2.Get<unit::time::TtMjd>();
    auto gpst2 = time2.Get<unit::time::GpstTime>();
    ASSERT_TRUE(tai2.ok() && tt2.ok() && gpst2.ok());

    EXPECT_GT(MjdDiffSeconds(tai2.value.mjd, tai1.value.mjd), 0.0);
    EXPECT_GT(MjdDiffSeconds(tt2.value.mjd, tt1.value.mjd), 0.0);
    double gpst_diff = (static_cast<double>(gpst2.value.week) -
                        static_cast<double>(gpst1.value.week)) *
                           unit::time::kSecPerWeek +
                       (gpst2.value.sec - gpst1.value.sec);
    EXPECT_GT(gpst_diff, 0.0);
}

/**
 * @verify{TimeSys_6_7}
 * @covers{unit::time::TimeSys::operator+}
 */
TEST(TimeSysOperators, AddSubtractOperators) {
    using namespace std::chrono_literals;

    unit::time::LeapSecondTable leap_seconds;
    ASSERT_TRUE(LoadLeapSeconds(leap_seconds));

    unit::time::TimeSys time;
    time.SetLeapSecondTable(leap_seconds);
    ASSERT_EQ(time.Set(unit::time::CivilTime{2018, 6, 1, 0, 0, 0.0}),
              unit::time::TimeError::kOk);

    auto t2 = time + 2min;
    auto d1 = t2 - time;
    ASSERT_TRUE(d1.ok());
    EXPECT_NEAR(d1.value.count(), 120.0, kTimeToleranceSec);

    auto t3 = t2 - 1.5s;
    auto d2 = t3 - time;
    ASSERT_TRUE(d2.ok());
    EXPECT_NEAR(d2.value.count(), 118.5, kTimeToleranceSec);
}

/**
 * @verify{TimeSys_6_7}
 * @covers{unit::time::TimeSys::operator+=}
 */
TEST(TimeSysOperators, InPlaceOperators) {
    using namespace std::chrono_literals;

    unit::time::LeapSecondTable leap_seconds;
    ASSERT_TRUE(LoadLeapSeconds(leap_seconds));

    unit::time::TimeSys base;
    base.SetLeapSecondTable(leap_seconds);
    ASSERT_EQ(base.Set(unit::time::CivilTime{2019, 5, 1, 0, 0, 0.0}),
              unit::time::TimeError::kOk);

    unit::time::TimeSys time = base;
    time += 1s;
    time -= 500ms;
    auto diff = time - base;
    ASSERT_TRUE(diff.ok());
    EXPECT_NEAR(diff.value.count(), 0.5, kTimeToleranceSec);
}

/**
 * @verify{TimeSys_6_8}
 * @covers{unit::time::TimeSys::operator-}
 */
TEST(TimeSysErrors, UninitializedReturnsError) {
    using namespace std::chrono_literals;

    unit::time::TimeSys time;
    auto                t2   = time + 1s;
    auto                diff = t2 - time;
    ASSERT_FALSE(diff.ok());
    EXPECT_EQ(diff.error, unit::time::TimeError::kUninitialized);
}
