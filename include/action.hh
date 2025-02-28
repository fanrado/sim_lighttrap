#ifndef ACTION_HH
#define ACTION_HH

#include "G4VUserActionInitialization.hh"

class MyActionInitialization : public G4VUserActionInitialization
{
public:
  MyActionInitialization();
  ~MyActionInitialization();

  virtual void Build() const; //runs particle gun and stepping
};

#endif
