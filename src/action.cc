#include "action.hh"
#include "generator.hh"
#include "run.hh"
#include "event.hh"
#include "stepping.hh"
#include "tracking.hh"

MyActionInitialization::MyActionInitialization()
{}

MyActionInitialization::~MyActionInitialization()
{}

void MyActionInitialization::Build() const
{
  MyPrimaryGenerator *generator = new MyPrimaryGenerator();
  SetUserAction(generator);

  MyRunAction *runAction = new MyRunAction();
  SetUserAction(runAction);

  MyEventAction *eventAction = new MyEventAction(runAction);
  SetUserAction(eventAction);

  MySteppingAction *steppingAction = new MySteppingAction(eventAction);
  SetUserAction(steppingAction);

  // Register the custom tracking action to record WLS photons.
  SetUserAction(new MyTrackingAction());
}
