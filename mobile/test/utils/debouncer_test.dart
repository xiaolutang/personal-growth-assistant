import 'package:fake_async/fake_async.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rizhi/utils/debouncer.dart';

void main() {
  // ----------------------------------------------------------
  // 默认延迟
  // ----------------------------------------------------------
  group('Debouncer 构造', () {
    test('默认延迟为 300ms — 299ms 未执行，300ms 已执行', () {
      fakeAsync((async) {
        final debouncer = Debouncer();
        int callCount = 0;
        debouncer.run(() => callCount++);

        // 299ms：尚未到期，不应执行
        async.elapse(const Duration(milliseconds: 299));
        expect(callCount, 0);

        // 再过 1ms：到达 300ms，action 应执行
        async.elapse(const Duration(milliseconds: 1));
        expect(callCount, 1);

        debouncer.dispose();
      });
    });

    test('可自定义延迟', () {
      fakeAsync((async) {
        final debouncer = Debouncer(delay: const Duration(milliseconds: 50));
        int callCount = 0;
        debouncer.run(() => callCount++);

        async.elapse(const Duration(milliseconds: 60));
        expect(callCount, 1);

        debouncer.dispose();
      });
    });
  });

  // ----------------------------------------------------------
  // run — 多次调用只执行最后一次
  // ----------------------------------------------------------
  group('Debouncer.run', () {
    test('300ms 内多次调用只执行最后一次 action', () {
      fakeAsync((async) {
        final debouncer = Debouncer();
        final results = <String>[];

        debouncer.run(() => results.add('A'));
        async.elapse(const Duration(milliseconds: 100));
        debouncer.run(() => results.add('B'));
        async.elapse(const Duration(milliseconds: 100));
        debouncer.run(() => results.add('C'));

        // 最后一次 run 到 300ms 后执行
        async.elapse(const Duration(milliseconds: 300));
        expect(results, ['C']);

        debouncer.dispose();
      });
    });

    test('延迟到期后 action 被执行', () {
      fakeAsync((async) {
        final debouncer = Debouncer(delay: const Duration(milliseconds: 50));
        int callCount = 0;
        debouncer.run(() => callCount++);

        async.elapse(const Duration(milliseconds: 60));
        expect(callCount, 1);

        debouncer.dispose();
      });
    });

    test('isActive 反映 Timer 状态', () {
      fakeAsync((async) {
        final debouncer = Debouncer(delay: const Duration(milliseconds: 100));

        expect(debouncer.isActive, isFalse);

        debouncer.run(() {});
        expect(debouncer.isActive, isTrue);

        async.elapse(const Duration(milliseconds: 150));
        expect(debouncer.isActive, isFalse);

        debouncer.dispose();
      });
    });

    test('Timer 回调执行后 isActive 自动变为 false', () {
      fakeAsync((async) {
        final debouncer = Debouncer();
        debouncer.run(() {});

        // 执行前
        expect(debouncer.isActive, isTrue);

        // Timer 触发后
        async.elapse(const Duration(milliseconds: 300));
        expect(debouncer.isActive, isFalse);

        debouncer.dispose();
      });
    });
  });

  // ----------------------------------------------------------
  // immediateRun — 立即执行
  // ----------------------------------------------------------
  group('Debouncer.immediateRun', () {
    test('立即执行不延迟', () {
      final debouncer = Debouncer();
      int callCount = 0;

      debouncer.immediateRun(() => callCount++);
      expect(callCount, 1);

      debouncer.dispose();
    });

    test('取消已排队的防抖任务后立即执行', () {
      fakeAsync((async) {
        final debouncer = Debouncer();
        final results = <String>[];

        debouncer.run(() => results.add('delayed'));
        // 在延迟到期前调用 immediateRun
        debouncer.immediateRun(() => results.add('immediate'));

        // 再过 400ms，确认 delayed 不会再执行
        async.elapse(const Duration(milliseconds: 400));
        expect(results, ['immediate']);

        debouncer.dispose();
      });
    });
  });

  // ----------------------------------------------------------
  // dispose — 取消 Timer
  // ----------------------------------------------------------
  group('Debouncer.dispose', () {
    test('dispose 后 Timer 被取消，action 不执行', () {
      fakeAsync((async) {
        final debouncer = Debouncer();
        int callCount = 0;

        debouncer.run(() => callCount++);
        debouncer.dispose();

        async.elapse(const Duration(milliseconds: 400));
        expect(callCount, 0);
      });
    });

    test('dispose 后 isActive 为 false', () {
      final debouncer = Debouncer();
      debouncer.run(() {});
      expect(debouncer.isActive, isTrue);

      debouncer.dispose();
      expect(debouncer.isActive, isFalse);
    });

    test('多次调用 dispose 不抛异常', () {
      final debouncer = Debouncer();
      debouncer.run(() {});

      // 应不抛异常
      debouncer.dispose();
      debouncer.dispose();
      debouncer.dispose();
    });
  });
}
