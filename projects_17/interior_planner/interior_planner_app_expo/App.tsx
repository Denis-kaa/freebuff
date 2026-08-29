import React from 'react';
import { StatusBar ***REMOVED*** from 'expo-status-bar';
import { GestureHandlerRootView ***REMOVED*** from 'react-native-gesture-handler';
import { SafeAreaProvider ***REMOVED*** from 'react-native-safe-area-context';
import RoomEditor from './src/components/RoomEditor';
export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 ***REMOVED******REMOVED***>
      <SafeAreaProvider>
        <RoomEditor />
        <StatusBar style="auto" />
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
***REMOVED***
