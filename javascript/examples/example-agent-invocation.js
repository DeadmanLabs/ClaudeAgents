#!/usr/bin/env node
/**
 * Example script demonstrating how to use ClaudeAgents to build a complete software solution.
 *
 * This example shows how to:
 * 1. Set up and configure the manager agent
 * 2. Execute a complex development task using all agent types
 * 3. Process and display the results
 */

const { setupLogger } = require('../src/utils/LoggerSetup');
const { MemoryManager } = require('../src/utils/MemoryManager');
const { ManagerAgent } = require('../src/agents/ManagerAgent');

async function runExample() {
  // Setup logging
  const logger = setupLogger({
    logLevel: 'info',
    logToFile: true,
    logFileDir: 'logs',
  });

  // Initialize memory manager with persistence
  const memoryManager = new MemoryManager(true, './memory');

  // Create the manager agent
  const manager = new ManagerAgent('Manager', memoryManager);

  // Example prompt that will require all agent functions
  const prompt = `
    Create a weather dashboard application with the following features:
    
    1. A responsive web interface that displays current weather and 5-day forecast
    2. Backend API that fetches data from a public weather API
    3. Ability to search for weather by city name or zip code
    4. Show temperature, humidity, wind speed, and weather conditions
    5. Store user's recent searches
    6. Display weather data using charts and icons
    7. Automatically detect user's location on initial load
    
    The solution should be easy to deploy and use Docker for containerization.
    Make it accessible for developers to extend with new features.
  `;

  console.log('\n' + '='.repeat(60));
  console.log(' ClaudeAgents - Multi-agent Collaborative Development Example ');
  console.log('='.repeat(60) + '\n');

  console.log(`🚀 Starting development process with prompt:\n${prompt}\n`);
  console.log('📋 This example will demonstrate the complete collaborative workflow using all agent types:\n');
  console.log('1. Manager Agent - Overall coordination');
  console.log('2. Architecture Designer - System architecture');
  console.log('3. Stack Builder - Technology stack setup');
  console.log('4. Library Researcher - Finding optimal libraries');
  console.log('5. Software Planner - Development planning');
  console.log('6. Software Programmer - Code implementation');
  console.log('7. Exception Debugger - Testing and debugging');
  console.log('8. Dependency Analyzer - Dependency management\n');

  // Execute the manager agent with the prompt
  try {
    console.log('⏳ Starting multi-agent process - this may take several minutes...\n');
    const result = await manager.execute(prompt);

    if (result.success) {
      console.log('\n✅ Process completed successfully!\n');

      // Access detailed results
      const finalResult = result.result || {};

      // Print summary
      console.log('📑 Solution Summary:');
      console.log(`  ${(finalResult.summary || 'No summary available').substring(0, 500)}...\n`);

      // Print architecture overview
      console.log('🏗️ Architecture Overview:');
      const architecture = finalResult.architecture || {};
      console.log(`  ${(architecture.summary || 'No architecture details available').substring(0, 300)}...\n`);

      // Print technology stack
      const libraries = finalResult.libraries || {};
      if (libraries.libraries && Array.isArray(libraries.libraries)) {
        console.log('📚 Selected Libraries:');
        for (const lib of libraries.libraries) {
          console.log(`  • ${lib.name || 'Unknown'}: ${(lib.description || 'No description').substring(0, 100)}`);
        }
      }

      // Print file summary
      const files = finalResult.files || {};
      if (Object.keys(files).length > 0) {
        console.log('\n💻 Generated Files:');
        for (const filename of Object.keys(files)) {
          console.log(`  • ${filename}`);
        }
      }

      console.log('\n📁 Full solution details saved to memory directory.');
    } else {
      console.log(`\n❌ Process failed: ${result.error || 'Unknown error'}`);
    }
  } catch (error) {
    logger.error(`Error in example: ${error.message}`);
    console.log(`\n❌ Error: ${error.message}`);
  }
}

// Run the example
runExample().catch(error => {
  console.error('Unhandled error in example:', error);
});