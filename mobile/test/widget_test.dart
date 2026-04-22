import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:growth_assistant/main.dart';

void main() {
  testWidgets('App renders title text', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: GrowthApp()));

    expect(find.text('个人成长助手'), findsOneWidget);
  });
}
